"""Read-model service and a small JSON REST API for the monitoring dashboard.

Uses only the standard library (``http.server``), which is enough for a
single-operator prototype. Endpoints:

    GET  /api/health
    GET  /api/config                      categories and statuses
    GET  /api/summary                     counts per SLA status, review queue size
    GET  /api/appeals?status=&category=&review=true&q=
    GET  /api/metrics                     classifier metrics (if available)
    POST /api/appeals/<id>/review         {"category": "..."} operator confirms a label

Any other path is served from the built React dashboard (``--static``).
"""

from __future__ import annotations

import json
import threading
from collections import Counter
from dataclasses import asdict, replace
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from appeal_agent.agent import AppealAgent
from appeal_agent.models import Appeal, ProcessedAppeal
from appeal_agent.sla import SLAStatus

# Most urgent first: this is the order in which an operator should act.
STATUS_PRIORITY = {
    SLAStatus.OVERDUE: 0,
    SLAStatus.AT_RISK: 1,
    SLAStatus.ON_TRACK: 2,
    SLAStatus.CLOSED_LATE: 3,
    SLAStatus.CLOSED_ON_TIME: 4,
}
OPEN_STATUSES = {SLAStatus.OVERDUE, SLAStatus.AT_RISK, SLAStatus.ON_TRACK}


class AppealNotFoundError(LookupError):
    pass


class DashboardService:
    """Holds processed appeals in memory and answers dashboard queries."""

    def __init__(
        self,
        agent: AppealAgent,
        appeals: list[Appeal],
        today: date,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        self.agent = agent
        self.today = today
        self.metrics = metrics
        self._appeals = {a.appeal_id: a for a in appeals}
        self._processed = {p.appeal_id: p for p in agent.process(appeals, today)}
        self._reviewed: set[str] = set()
        self._lock = threading.Lock()

    def _to_json(self, item: ProcessedAppeal) -> dict[str, Any]:
        row = asdict(item)
        row["submitted_on"] = item.submitted_on.isoformat()
        row["deadline"] = item.deadline.isoformat()
        row["status"] = item.status.value
        row["reviewed"] = item.appeal_id in self._reviewed
        return row

    def config(self) -> dict[str, Any]:
        return {
            "categories": list(self.agent.config.categories),
            "statuses": [s.value for s in STATUS_PRIORITY],
        }

    def summary(self) -> dict[str, Any]:
        items = list(self._processed.values())
        counts = Counter(p.status for p in items)
        open_by_category = Counter(p.category for p in items if p.status in OPEN_STATUSES)
        return {
            "today": self.today.isoformat(),
            "model_version": self.agent.classifier.version,
            "total": len(items),
            "by_status": {s.value: counts.get(s, 0) for s in STATUS_PRIORITY},
            "open_by_category": {
                c: open_by_category.get(c, 0) for c in self.agent.config.categories
            },
            "needs_review": sum(p.needs_review for p in items),
            "urgent_open": sum(p.urgent for p in items if p.status in OPEN_STATUSES),
        }

    def appeals(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        review: bool | None = None,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        items: list[ProcessedAppeal] = list(self._processed.values())
        if status:
            items = [p for p in items if p.status.value == status]
        if category:
            items = [p for p in items if p.category == category]
        if review is not None:
            items = [p for p in items if p.needs_review is review]
        if query:
            needle = query.lower()
            items = [
                p
                for p in items
                if needle in p.masked_text.lower()
                or needle in p.location.lower()
                or needle in p.appeal_id.lower()
            ]
        ordered = sorted(
            items,
            key=lambda p: (STATUS_PRIORITY[p.status], p.remaining_business_days, p.appeal_id),
        )
        return [self._to_json(p) for p in ordered]

    def confirm_category(self, appeal_id: str, category: str) -> dict[str, Any]:
        """Operator decision from the review queue: fix the label and re-evaluate the SLA."""
        if category not in self.agent.config.categories:
            raise ValueError(f"unknown category: {category}")
        with self._lock:
            if appeal_id not in self._processed:
                raise AppealNotFoundError(appeal_id)
            current = self._processed[appeal_id]
            appeal = self._appeals[appeal_id]
            sla = self.agent.sla.evaluate(
                appeal.submitted_on,
                category,
                self.today,
                urgent=current.urgent,
                closed_on=appeal.closed_on,
            )
            updated = replace(
                current,
                category=category,
                confidence=1.0,
                needs_review=False,
                deadline=sla.deadline,
                remaining_business_days=sla.remaining_business_days,
                status=sla.status,
            )
            self._processed[appeal_id] = updated
            self._reviewed.add(appeal_id)
            return self._to_json(updated)


def _flag(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return value.lower() in {"1", "true", "yes"}


def make_handler(
    service: DashboardService, static_dir: Path | None
) -> type[BaseHTTPRequestHandler]:
    static_root = static_dir.resolve() if static_dir else None

    class Handler(BaseHTTPRequestHandler):
        server_version = "AppealAgent/0.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass  # keep the console clean; the CLI prints the URL once

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._send_json({"error": message}, status)

        def do_GET(self) -> None:  # noqa: N802 (name required by http.server)
            url = urlparse(self.path)
            params = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path == "/api/health":
                self._send_json({"status": "ok"})
            elif url.path == "/api/config":
                self._send_json(service.config())
            elif url.path == "/api/summary":
                self._send_json(service.summary())
            elif url.path == "/api/metrics":
                if service.metrics is None:
                    self._error(HTTPStatus.NOT_FOUND, "no metrics available; run `train` first")
                else:
                    self._send_json(service.metrics)
            elif url.path == "/api/appeals":
                self._send_json(
                    service.appeals(
                        status=params.get("status"),
                        category=params.get("category"),
                        review=_flag(params.get("review")),
                        query=params.get("q"),
                    )
                )
            elif url.path.startswith("/api/"):
                self._error(HTTPStatus.NOT_FOUND, "unknown endpoint")
            else:
                self._serve_static(url.path)

        def do_POST(self) -> None:  # noqa: N802
            parts = urlparse(self.path).path.strip("/").split("/")
            if len(parts) != 4 or parts[:2] != ["api", "appeals"] or parts[3] != "review":
                self._error(HTTPStatus.NOT_FOUND, "unknown endpoint")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                category = body["category"]
                self._send_json(service.confirm_category(unquote(parts[2]), category))
            except AppealNotFoundError:
                self._error(HTTPStatus.NOT_FOUND, "appeal not found")
            except (ValueError, KeyError, TypeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, f"invalid request: {exc}")

        def _serve_static(self, path: str) -> None:
            if static_root is None:
                self._error(HTTPStatus.NOT_FOUND, "dashboard is not built; see dashboard/README")
                return
            target = (static_root / unquote(path).lstrip("/")).resolve()
            if not target.is_relative_to(static_root):
                self._error(HTTPStatus.FORBIDDEN, "forbidden")
                return
            if not target.is_file():
                target = static_root / "index.html"  # single-page app fallback
            if not target.is_file():
                self._error(HTTPStatus.NOT_FOUND, "index.html not found")
                return
            types = {
                ".html": "text/html",
                ".js": "text/javascript",
                ".css": "text/css",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".ico": "image/x-icon",
            }
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", types.get(target.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def create_server(
    service: DashboardService, host: str, port: int, static_dir: Path | None = None
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(service, static_dir))

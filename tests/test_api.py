"""Dashboard service and the REST API (real HTTP server on a free port)."""

from __future__ import annotations

import argparse
import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from appeal_agent.agent import AppealAgent
from appeal_agent.api import (
    AppealAlreadyClosedError,
    AppealNotFoundError,
    DashboardService,
    create_server,
)
from appeal_agent.classifier import AppealClassifier
from appeal_agent.cli import _load_service
from appeal_agent.config import AgentConfig
from appeal_agent.data_gen import generate_appeals
from appeal_agent.io import read_appeals, write_appeals

TODAY = date(2026, 10, 5)
ORDER = ["overdue", "at_risk", "on_track", "closed_late", "closed_on_time"]


@pytest.fixture
def service(config: AgentConfig, trained_model: AppealClassifier) -> DashboardService:
    appeals = generate_appeals(150, seed=21, reference_date=TODAY)
    return DashboardService(AppealAgent(config, trained_model), appeals, TODAY, {"accuracy": 0.9})


def test_summary_counts_add_up(service: DashboardService) -> None:
    summary = service.summary()
    assert summary["total"] == 150
    assert sum(summary["by_status"].values()) == 150
    assert list(summary["by_status"]) == ORDER
    assert set(summary["open_by_category"]) == set(service.config()["categories"])


def test_appeals_sorted_by_urgency(service: DashboardService) -> None:
    rows = service.appeals()
    ranks = [ORDER.index(r["status"]) for r in rows]
    assert ranks == sorted(ranks)
    assert isinstance(rows[0]["deadline"], str)


def test_filters(service: DashboardService) -> None:
    assert all(r["status"] == "overdue" for r in service.appeals(status="overdue"))
    assert all(r["category"] == "water" for r in service.appeals(category="water"))
    assert all(r["needs_review"] for r in service.appeals(review=True))
    first = service.appeals()[0]
    assert [r["appeal_id"] for r in service.appeals(query=first["appeal_id"])] == [
        first["appeal_id"]
    ]


def test_confirm_category_updates_sla(service: DashboardService) -> None:
    row = service.appeals()[0]
    updated = service.confirm_category(row["appeal_id"], "water")
    assert updated["category"] == "water"
    assert updated["reviewed"] is True and updated["needs_review"] is False
    assert updated["confidence"] == 1.0
    with pytest.raises(ValueError):
        service.confirm_category(row["appeal_id"], "spaceships")
    with pytest.raises(AppealNotFoundError):
        service.confirm_category("missing", "water")


def test_close_appeal(service: DashboardService) -> None:
    overdue = service.appeals(status="overdue")[0]
    closed = service.close_appeal(overdue["appeal_id"])
    assert closed["status"] == "closed_late"
    assert closed["closed_on"] == TODAY.isoformat()
    assert service.summary()["by_status"]["overdue"] == len(service.appeals(status="overdue"))
    on_track = service.appeals(status="on_track")[0]
    assert service.close_appeal(on_track["appeal_id"])["status"] == "closed_on_time"
    with pytest.raises(AppealAlreadyClosedError):
        service.close_appeal(overdue["appeal_id"])
    with pytest.raises(AppealNotFoundError):
        service.close_appeal("missing")


def test_close_appeal_is_saved_to_csv(
    config: AgentConfig, trained_model: AppealClassifier, tmp_path: Path
) -> None:
    path = tmp_path / "appeals.csv"
    write_appeals(generate_appeals(30, seed=3, reference_date=TODAY), path)
    service = DashboardService(
        AppealAgent(config, trained_model), read_appeals(path), TODAY, data_path=path
    )
    appeal_id = service.appeals(status="overdue")[0]["appeal_id"]
    service.close_appeal(appeal_id)
    saved = {a.appeal_id: a for a in read_appeals(path)}
    assert len(saved) == 30 and saved[appeal_id].closed_on == TODAY
    assert not (tmp_path / "appeals.csv.tmp").exists()


@pytest.fixture
def base_url(service: DashboardService, tmp_path: Path) -> Iterator[str]:
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("<h1>dashboard</h1>", encoding="utf-8")
    (static / "app.js").write_text("console.log(1)", encoding="utf-8")
    server = create_server(service, "127.0.0.1", 0, static)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _get(url: str) -> tuple[int, Any, str]:
    try:
        with urllib.request.urlopen(url) as resp:
            body = resp.read().decode()
            ctype = resp.headers["Content-Type"]
            return resp.status, json.loads(body) if "json" in ctype else body, ctype
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode()), err.headers["Content-Type"]


def _post(url: str, payload: Any) -> tuple[int, Any]:
    data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode())


def test_http_get_endpoints(base_url: str) -> None:
    assert _get(f"{base_url}/api/health")[1] == {"status": "ok"}
    assert "categories" in _get(f"{base_url}/api/config")[1]
    assert _get(f"{base_url}/api/summary")[1]["total"] == 150
    assert _get(f"{base_url}/api/metrics")[1] == {"accuracy": 0.9}
    status, rows, _ = _get(f"{base_url}/api/appeals?status=overdue&review=")
    assert status == 200 and all(r["status"] == "overdue" for r in rows)
    assert _get(f"{base_url}/api/nope")[0] == 404


def test_http_review(base_url: str) -> None:
    appeal_id = _get(f"{base_url}/api/appeals?review=true")[1][0]["appeal_id"]
    status, row = _post(f"{base_url}/api/appeals/{appeal_id}/review", {"category": "roads"})
    assert status == 200 and row["category"] == "roads" and row["reviewed"]
    assert _post(f"{base_url}/api/appeals/missing/review", {"category": "roads"})[0] == 404
    assert _post(f"{base_url}/api/appeals/{appeal_id}/review", {"category": "x"})[0] == 400
    assert _post(f"{base_url}/api/appeals/{appeal_id}/review", b"not json")[0] == 400
    assert _post(f"{base_url}/api/other", {})[0] == 404


def test_http_close(base_url: str) -> None:
    appeal_id = _get(f"{base_url}/api/appeals?status=overdue")[1][0]["appeal_id"]
    status, row = _post(f"{base_url}/api/appeals/{appeal_id}/close", b"")
    assert status == 200 and row["status"] == "closed_late" and row["closed_on"]
    assert _post(f"{base_url}/api/appeals/{appeal_id}/close", b"")[0] == 409
    assert _post(f"{base_url}/api/appeals/missing/close", b"")[0] == 404


def test_static_files_and_spa_fallback(base_url: str) -> None:
    assert _get(f"{base_url}/")[1] == "<h1>dashboard</h1>"
    status, body, ctype = _get(f"{base_url}/app.js")
    assert status == 200 and ctype == "text/javascript"
    assert _get(f"{base_url}/some/client/route")[1] == "<h1>dashboard</h1>"
    assert _get(f"{base_url}/..%2f..%2fetc/passwd")[0] == 403


def test_missing_metrics_and_static(config: AgentConfig, trained_model: AppealClassifier) -> None:
    service = DashboardService(AppealAgent(config, trained_model), [], TODAY)
    server = create_server(service, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert _get(f"{url}/api/metrics")[0] == 404
        assert _get(f"{url}/")[0] == 404
    finally:
        server.shutdown()
        server.server_close()


def test_load_service_from_files(trained_model: AppealClassifier, tmp_path: Path) -> None:
    write_appeals(generate_appeals(20, seed=4), tmp_path / "a.csv")
    trained_model.save(tmp_path / "m.joblib")
    args = argparse.Namespace(
        config=None,
        data=tmp_path / "a.csv",
        model=tmp_path / "m.joblib",
        metrics=tmp_path / "none.json",
        today=TODAY,
    )
    service = _load_service(args)
    assert service.summary()["total"] == 20 and service.metrics is None

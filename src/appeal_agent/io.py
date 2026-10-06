"""CSV input/output for appeals and processed results."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import asdict, fields
from datetime import date
from pathlib import Path

from appeal_agent.models import Appeal, ProcessedAppeal

APPEAL_COLUMNS = [f.name for f in fields(Appeal)]
PROCESSED_COLUMNS = [f.name for f in fields(ProcessedAppeal)]


def _optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def write_appeals(appeals: Iterable[Appeal], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=APPEAL_COLUMNS)
        writer.writeheader()
        for appeal in appeals:
            row = asdict(appeal)
            writer.writerow({k: "" if v is None else v for k, v in row.items()})


def read_appeals(path: str | Path) -> list[Appeal]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = {"appeal_id", "submitted_on", "text"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing required columns {sorted(missing)}")
        return [
            Appeal(
                appeal_id=row["appeal_id"],
                submitted_on=date.fromisoformat(row["submitted_on"]),
                text=row["text"],
                location=row.get("location") or "",
                category=row.get("category") or None,
                closed_on=_optional_date(row.get("closed_on")),
            )
            for row in reader
        ]


def write_processed(processed: Iterable[ProcessedAppeal], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=PROCESSED_COLUMNS)
        writer.writeheader()
        for item in processed:
            row = asdict(item)
            row["status"] = item.status.value
            writer.writerow(row)

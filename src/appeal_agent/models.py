from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from appeal_agent.sla import SLAStatus


@dataclass(frozen=True)
class Appeal:
    appeal_id: str
    submitted_on: date
    text: str
    location: str = ""
    category: str | None = None
    closed_on: date | None = None


@dataclass(frozen=True)
class ProcessedAppeal:
    appeal_id: str
    submitted_on: date
    masked_text: str
    location: str
    category: str
    confidence: float
    needs_review: bool
    urgent: bool
    deadline: date
    remaining_business_days: int
    status: SLAStatus
    model_version: str
    closed_on: date | None = None

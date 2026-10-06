"""SLA (regulatory deadline) engine for citizen appeals."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from appeal_agent.business_calendar import BusinessCalendar


class SLAStatus(StrEnum):
    """Status of an appeal relative to its regulatory deadline."""

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OVERDUE = "overdue"
    CLOSED_ON_TIME = "closed_on_time"
    CLOSED_LATE = "closed_late"


@dataclass(frozen=True)
class SLARule:
    """Response term for one appeal category, in business days.

    Attributes:
        term_days: Regular response term.
        warning_days: The appeal becomes *at risk* when this many business
            days or fewer remain before the deadline.
        urgent_term_days: Shorter term applied to urgent appeals. ``None``
            means urgent appeals use ``term_days``.
    """

    term_days: int
    warning_days: int
    urgent_term_days: int | None = None

    def __post_init__(self) -> None:
        if self.term_days <= 0:
            raise ValueError("term_days must be positive")
        if not 0 <= self.warning_days < self.term_days:
            raise ValueError("warning_days must be in [0, term_days)")
        if self.urgent_term_days is not None and not 0 < self.urgent_term_days <= self.term_days:
            raise ValueError("urgent_term_days must be in (0, term_days]")

    def term_for(self, urgent: bool) -> int:
        if urgent and self.urgent_term_days is not None:
            return self.urgent_term_days
        return self.term_days


@dataclass(frozen=True)
class SLAEvaluation:
    deadline: date
    remaining_business_days: int
    status: SLAStatus


class SLAEngine:
    """Calculates deadlines and SLA statuses from configurable rules."""

    def __init__(
        self,
        calendar: BusinessCalendar,
        rules: Mapping[str, SLARule],
        default_rule: SLARule,
    ) -> None:
        self.calendar = calendar
        self.rules = dict(rules)
        self.default_rule = default_rule

    def rule_for(self, category: str) -> SLARule:
        return self.rules.get(category, self.default_rule)

    def deadline(self, submitted_on: date, category: str, urgent: bool = False) -> date:
        """Regulatory deadline: the n-th business day after submission."""
        term = self.rule_for(category).term_for(urgent)
        return self.calendar.add_business_days(submitted_on, term)

    def evaluate(
        self,
        submitted_on: date,
        category: str,
        today: date,
        *,
        urgent: bool = False,
        closed_on: date | None = None,
    ) -> SLAEvaluation:
        """Evaluate the SLA status of one appeal on a given day.

        An open appeal is *overdue* once ``today`` is past the deadline, *at
        risk* when ``warning_days`` or fewer business days remain (including the
        deadline day itself, when 0 remain) and *on track* otherwise.
        """
        rule = self.rule_for(category)
        deadline = self.deadline(submitted_on, category, urgent)

        if closed_on is not None:
            remaining = self.calendar.business_days_between(closed_on, deadline)
            status = SLAStatus.CLOSED_ON_TIME if closed_on <= deadline else SLAStatus.CLOSED_LATE
            return SLAEvaluation(deadline, remaining, status)

        remaining = self.calendar.business_days_between(today, deadline)
        if today > deadline:
            status = SLAStatus.OVERDUE
        elif remaining <= rule.warning_days:
            status = SLAStatus.AT_RISK
        else:
            status = SLAStatus.ON_TRACK
        return SLAEvaluation(deadline, remaining, status)

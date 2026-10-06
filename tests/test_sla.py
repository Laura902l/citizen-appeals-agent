from datetime import date

import pytest

from appeal_agent.sla import SLAEngine, SLARule, SLAStatus

SUBMITTED = date(2026, 10, 1)  # Thursday; water term 10 days -> deadline Thu 15 Oct


def test_deadline_counts_business_days(engine: SLAEngine) -> None:
    assert engine.deadline(SUBMITTED, "water") == date(2026, 10, 15)


def test_urgent_term_is_shorter(engine: SLAEngine) -> None:
    assert engine.deadline(SUBMITTED, "water", urgent=True) == date(2026, 10, 5)


def test_urgent_without_special_term_uses_regular_term(engine: SLAEngine) -> None:
    assert engine.deadline(SUBMITTED, "roads", urgent=True) == engine.deadline(SUBMITTED, "roads")


def test_unknown_category_uses_default_rule(engine: SLAEngine) -> None:
    assert engine.rule_for("unknown") == engine.default_rule


@pytest.mark.parametrize(
    ("today", "status", "remaining"),
    [
        (date(2026, 10, 2), SLAStatus.ON_TRACK, 9),
        (date(2026, 10, 12), SLAStatus.ON_TRACK, 3),
        (date(2026, 10, 13), SLAStatus.AT_RISK, 2),
        (date(2026, 10, 15), SLAStatus.AT_RISK, 0),  # deadline day is still not overdue
        (date(2026, 10, 16), SLAStatus.OVERDUE, -1),
        (date(2026, 10, 19), SLAStatus.OVERDUE, -2),
    ],
)
def test_status_transitions(
    engine: SLAEngine, today: date, status: SLAStatus, remaining: int
) -> None:
    result = engine.evaluate(SUBMITTED, "water", today)
    assert result.status is status
    assert result.remaining_business_days == remaining


def test_weekend_after_deadline_is_overdue(engine: SLAEngine) -> None:
    # Saturday after the Thursday deadline: zero business days passed, but overdue.
    result = engine.evaluate(SUBMITTED, "water", date(2026, 10, 17))
    assert result.status is SLAStatus.OVERDUE


def test_closed_on_time_and_late(engine: SLAEngine) -> None:
    on_time = engine.evaluate(SUBMITTED, "water", date(2026, 11, 1), closed_on=date(2026, 10, 14))
    late = engine.evaluate(SUBMITTED, "water", date(2026, 11, 1), closed_on=date(2026, 10, 20))
    assert on_time.status is SLAStatus.CLOSED_ON_TIME
    assert late.status is SLAStatus.CLOSED_LATE


def test_deadline_shifted_by_holiday(engine: SLAEngine) -> None:
    # Term crossing the 26 Oct holiday ends one day later than without it.
    assert engine.deadline(date(2026, 10, 22), "water") == date(2026, 11, 6)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"term_days": 0, "warning_days": 0},
        {"term_days": 5, "warning_days": 5},
        {"term_days": 5, "warning_days": -1},
        {"term_days": 5, "warning_days": 1, "urgent_term_days": 6},
        {"term_days": 5, "warning_days": 1, "urgent_term_days": 0},
    ],
)
def test_invalid_rules_rejected(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        SLARule(**kwargs)

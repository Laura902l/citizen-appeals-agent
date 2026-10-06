from datetime import date

import pytest

from appeal_agent.business_calendar import BusinessCalendar

HOLIDAY = date(2026, 10, 26)  # same holiday as in conftest


def test_weekend_and_holiday_are_not_business_days(calendar: BusinessCalendar) -> None:
    assert calendar.is_business_day(date(2026, 10, 23))  # Friday
    assert not calendar.is_business_day(date(2026, 10, 24))  # Saturday
    assert not calendar.is_business_day(date(2026, 10, 25))  # Sunday
    assert not calendar.is_business_day(HOLIDAY)


def test_friday_plus_one_skips_weekend() -> None:
    assert BusinessCalendar().add_business_days(date(2026, 10, 2), 1) == date(2026, 10, 5)


def test_long_weekend_before_holiday(calendar: BusinessCalendar) -> None:
    # Submitted Friday before a long weekend (Sat, Sun, holiday Monday) -> Tuesday.
    assert calendar.add_business_days(date(2026, 10, 23), 1) == date(2026, 10, 27)


def test_day_after_holiday(calendar: BusinessCalendar) -> None:
    # Submitted on the holiday itself: the term starts from the next working day.
    assert calendar.add_business_days(HOLIDAY, 1) == date(2026, 10, 27)


def test_month_end_boundary(calendar: BusinessCalendar) -> None:
    assert calendar.add_business_days(date(2026, 9, 30), 2) == date(2026, 10, 2)


def test_year_end_boundary(calendar: BusinessCalendar) -> None:
    # 31 Dec 2026 (Thu) + 1: Fri 1 Jan 2027 is a holiday, then a weekend -> Mon 4 Jan.
    assert calendar.add_business_days(date(2026, 12, 31), 1) == date(2027, 1, 4)


def test_zero_days_returns_start(calendar: BusinessCalendar) -> None:
    assert calendar.add_business_days(date(2026, 10, 24), 0) == date(2026, 10, 24)


def test_negative_days_rejected(calendar: BusinessCalendar) -> None:
    with pytest.raises(ValueError):
        calendar.add_business_days(date(2026, 10, 1), -1)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2026, 10, 5), date(2026, 10, 5), 0),
        (date(2026, 10, 5), date(2026, 10, 9), 4),
        (date(2026, 10, 9), date(2026, 10, 12), 1),  # over a weekend
        (date(2026, 10, 23), date(2026, 10, 27), 1),  # over weekend + holiday
        (date(2026, 10, 12), date(2026, 10, 9), -1),  # negative direction
    ],
)
def test_business_days_between(
    calendar: BusinessCalendar, start: date, end: date, expected: int
) -> None:
    assert calendar.business_days_between(start, end) == expected


def test_between_is_inverse_of_add(calendar: BusinessCalendar) -> None:
    start = date(2026, 10, 1)
    for n in range(0, 40):
        assert calendar.business_days_between(start, calendar.add_business_days(start, n)) == n


def test_custom_weekend() -> None:
    # Friday-Saturday weekend.
    cal = BusinessCalendar(weekend=[4, 5])
    assert cal.add_business_days(date(2026, 10, 1), 1) == date(2026, 10, 4)  # Thu -> Sun


@pytest.mark.parametrize("weekend", [[7], list(range(7))])
def test_invalid_weekend(weekend: list[int]) -> None:
    with pytest.raises(ValueError):
        BusinessCalendar(weekend=weekend)

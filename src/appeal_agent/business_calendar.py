"""Business-day arithmetic with a configurable weekend and holiday calendar.

Convention used throughout the project: the submission day itself is never
counted. A term of ``n`` business days ends on the ``n``-th business day
*after* the submission date.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

_ONE_DAY = timedelta(days=1)


class BusinessCalendar:
    """Calendar that knows which dates are working days.

    Args:
        holidays: Public holidays (non-working days) in addition to the weekend.
        weekend: Weekday numbers treated as non-working (Monday=0 ... Sunday=6).
    """

    def __init__(self, holidays: Iterable[date] = (), weekend: Iterable[int] = (5, 6)) -> None:
        self._holidays = frozenset(holidays)
        self._weekend = frozenset(weekend)
        if not self._weekend.issubset(range(7)):
            raise ValueError("weekend days must be integers between 0 (Mon) and 6 (Sun)")
        if len(self._weekend) == 7:
            raise ValueError("a calendar needs at least one working weekday")

    @property
    def holidays(self) -> frozenset[date]:
        return self._holidays

    def is_business_day(self, day: date) -> bool:
        """Return ``True`` if ``day`` is neither a weekend day nor a holiday."""
        return day.weekday() not in self._weekend and day not in self._holidays

    def add_business_days(self, start: date, days: int) -> date:
        """Return the ``days``-th business day after ``start``.

        ``start`` itself is not counted, so ``add_business_days(friday, 1)`` is
        the following Monday (if Monday is a working day).
        """
        if days < 0:
            raise ValueError("days must be non-negative")
        current = start
        remaining = days
        while remaining > 0:
            current += _ONE_DAY
            if self.is_business_day(current):
                remaining -= 1
        return current

    def business_days_between(self, start: date, end: date) -> int:
        """Count business days in the half-open interval ``(start, end]``.

        The result is negative when ``end`` is before ``start``, which makes it
        convenient for "remaining days until the deadline" calculations.
        """
        if end == start:
            return 0
        sign = 1 if end > start else -1
        low, high = (start, end) if sign == 1 else (end, start)
        count = 0
        current = low
        while current < high:
            current += _ONE_DAY
            if self.is_business_day(current):
                count += 1
        return sign * count

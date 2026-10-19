"""Date rules of schedules: on which dates a schedule runs (concept 19.10, 18.2 RecurrenceFactory).

A rule only knows dates; the time of day is added by `wall_time.py` and the sun triggers. The
rules need only the standard library besides the `Repeat` data class.
"""

from __future__ import annotations

from calendar import isleap, monthrange
from collections.abc import Callable, Collection
from datetime import date, timedelta
from typing import Protocol

from .model import Repeat, RepeatFreq

LOOKBACK_DAYS = 400
"""Days `previous_date` looks back; the longest gap between two runs is a year (concept 19.10)."""

WEEK_STEPS = 3
"""Weeks `WeeklyRule` looks at to find the next date: the current one and the next matching one."""

MONTH_STEPS = 2
"""Months `MonthlyRule` looks at: the matching month and the one after it."""

_EPOCH = date(1970, 1, 1)
"""Anchor of the interval for a rule without `start_date`; only an interval of 1 can lack one."""

DAY = timedelta(days=1)


class DateRule(Protocol):
    """The dates of one schedule; `after` and `before` are local dates."""

    def matches(self, day: date) -> bool:
        """Return whether the schedule runs on `day`."""

    def next_date(self, after: date) -> date | None:
        """Return the first run date strictly after `after`, or None if the rule has ended."""

    def previous_date(self, before: date) -> date | None:
        """Return the last run date on or before `before`, or None if there is none."""


def _monday(day: date) -> date:
    """Return the Monday of the ISO week of `day`."""
    return day - timedelta(days=day.weekday())


def _month_index(day: date) -> int:
    """Return the number of the month of `day` since year 0."""
    return day.year * 12 + day.month - 1


class _BoundedRule:
    """Base of the rules: the first and last date, and the search for the next and previous date."""

    def __init__(self, start: date | None, end: date | None) -> None:
        """Remember the first and last date a run may happen; either may be missing."""
        self._start = start
        self._end = end

    def _fits(self, day: date) -> bool:
        """Return whether `day` lies on the pattern of the rule, ignoring start and end."""
        raise NotImplementedError

    def _first_from(self, day: date) -> date | None:
        """Return the first date on or after `day` that lies on the pattern, ignoring the end."""
        raise NotImplementedError

    def _in_range(self, day: date) -> bool:
        """Return whether `day` is neither before the start date nor after the end date."""
        return (self._start is None or day >= self._start) and (
            self._end is None or day <= self._end
        )

    def matches(self, day: date) -> bool:
        """Return whether the schedule runs on `day`."""
        return self._in_range(day) and self._fits(day)

    def next_date(self, after: date) -> date | None:
        """Return the first run date strictly after `after`, or None if the rule has ended."""
        try:
            first = after + DAY
            if self._start is not None and first < self._start:
                first = self._start
            found = self._first_from(first)
        except OverflowError, ValueError:  # the calendar ends at year 9999
            return None
        if found is None or (self._end is not None and found > self._end):
            return None
        return found

    def previous_date(self, before: date) -> date | None:
        """Return the last run date on or before `before`, or None if there is none."""
        day = before if self._end is None else min(before, self._end)
        for _ in range(LOOKBACK_DAYS):
            if self._start is not None and day < self._start:
                return None
            if self._fits(day):
                return day
            day -= DAY
        return None


class OnceRule(_BoundedRule):
    """Exactly one date."""

    def __init__(self, day: date | None) -> None:
        """Remember the date of the single run."""
        super().__init__(day, day)

    def _fits(self, day: date) -> bool:
        """Return whether a date is set; the range of start and end already is that single date."""
        return self._start is not None

    def _first_from(self, day: date) -> date | None:
        """Return the date if it is not before `day`."""
        return self._start if self._start is not None and self._start >= day else None


class DailyRule(_BoundedRule):
    """Every N days, counted from the start date."""

    def __init__(self, repeat: Repeat) -> None:
        """Remember the interval and the dates."""
        super().__init__(repeat.start_date, repeat.end_date)
        self._anchor = repeat.start_date or _EPOCH
        self._interval = repeat.interval

    def _fits(self, day: date) -> bool:
        """Return whether the number of days since the start date is a multiple of the interval."""
        return (day - self._anchor).days % self._interval == 0

    def _first_from(self, day: date) -> date | None:
        """Return `day` or the next day of the interval."""
        behind = (day - self._anchor).days % self._interval
        return day if behind == 0 else day + timedelta(days=self._interval - behind)


class WeeklyRule(_BoundedRule):
    """The chosen weekdays of every N-th ISO week, counted from the week of the start date."""

    def __init__(self, repeat: Repeat, days: Collection[int]) -> None:
        """Remember the interval, the weekdays and the dates."""
        super().__init__(repeat.start_date, repeat.end_date)
        self._anchor = _monday(repeat.start_date or _EPOCH)
        self._interval = repeat.interval
        self._days = frozenset(days)

    def _week_behind(self, day: date) -> int:
        """Return how many weeks past the last week of the interval `day` lies."""
        return ((_monday(day) - self._anchor).days // 7) % self._interval

    def _fits(self, day: date) -> bool:
        """Return whether the weekday is chosen and the week is one of the interval."""
        return day.weekday() in self._days and self._week_behind(day) == 0

    def _first_from(self, day: date) -> date | None:
        """Return the first chosen weekday on or after `day` in a week of the interval."""
        for _ in range(WEEK_STEPS):
            behind = self._week_behind(day)
            if behind:
                day = _monday(day) + timedelta(weeks=self._interval - behind)
            for weekday in range(day.weekday(), 7):
                if weekday in self._days:
                    return _monday(day) + timedelta(days=weekday)
            day = _monday(day) + timedelta(weeks=1)
        return None


class MonthlyRule(_BoundedRule):
    """The day of month of the start date in every N-th month; a missing day is the month's last."""

    def __init__(self, repeat: Repeat) -> None:
        """Remember the interval, the day of month and the dates."""
        super().__init__(repeat.start_date, repeat.end_date)
        self._anchor = repeat.start_date or _EPOCH
        self._interval = repeat.interval

    def _day_in(self, month_index: int) -> date:
        """Return the run date of a month: the anchor's day, or the last day of a shorter month."""
        year, month = divmod(month_index, 12)
        return date(year, month + 1, min(self._anchor.day, monthrange(year, month + 1)[1]))

    def _month_behind(self, day: date) -> int:
        """Return how many months past the last month of the interval `day` lies."""
        return (_month_index(day) - _month_index(self._anchor)) % self._interval

    def _fits(self, day: date) -> bool:
        """Return whether the month is one of the interval and `day` is its run date."""
        return self._month_behind(day) == 0 and day == self._day_in(_month_index(day))

    def _first_from(self, day: date) -> date | None:
        """Return the first run date on or after `day`."""
        index = _month_index(day)
        index += (self._interval - self._month_behind(day)) % self._interval
        for _ in range(MONTH_STEPS):
            candidate = self._day_in(index)
            if candidate >= day:
                return candidate
            index += self._interval
        return None


class YearlyRule(_BoundedRule):
    """The day and month of the start date every year; 29 February is 28 February in other years."""

    def __init__(self, repeat: Repeat) -> None:
        """Remember the day, the month and the dates."""
        super().__init__(repeat.start_date, repeat.end_date)
        self._anchor = repeat.start_date or _EPOCH

    def _day_in(self, year: int) -> date:
        """Return the run date of a year."""
        if (self._anchor.month, self._anchor.day) == (2, 29) and not isleap(year):
            return date(year, 2, 28)
        return date(year, self._anchor.month, self._anchor.day)

    def _fits(self, day: date) -> bool:
        """Return whether `day` is the run date of its year."""
        return day == self._day_in(day.year)

    def _first_from(self, day: date) -> date | None:
        """Return the first run date on or after `day`."""
        candidate = self._day_in(day.year)
        return candidate if candidate >= day else self._day_in(day.year + 1)


class RecurrenceFactory:
    """Creates the date rule that belongs to a schedule's `repeat.freq` (concept 18.2)."""

    def create(self, repeat: Repeat, days: Collection[int]) -> DateRule:
        """Return the rule for `repeat`; `days` are the weekdays of `when`, used by `weekly` only."""
        builders: dict[RepeatFreq, Callable[[], DateRule]] = {
            RepeatFreq.ONCE: lambda: OnceRule(repeat.start_date),
            RepeatFreq.DAILY: lambda: DailyRule(repeat),
            RepeatFreq.WEEKLY: lambda: WeeklyRule(repeat, days),
            RepeatFreq.MONTHLY: lambda: MonthlyRule(repeat),
            RepeatFreq.YEARLY: lambda: YearlyRule(repeat),
        }
        return builders[repeat.freq]()

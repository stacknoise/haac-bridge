"""Next and previous run of a fixed wall-clock time on the dates of a rule, DST-safe (concept 19.3 step 4).

This module needs only the standard library, so the time arithmetic can be tested on its own.
HA's `find_next_time_expression_time` is not used: it skips the whole day when the wall time falls
into a DST gap, but a schedule must still run on that day.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta, tzinfo
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .recurrence import DateRule

CANDIDATE_DATES = 5
"""Run dates looked at on each side of the time: the day before, the day and the next ones."""

DAY = timedelta(days=1)

MAX_GAP_MINUTES = 180
"""Longest DST gap (in minutes) the search steps through; real gaps are 30 or 60 minutes."""


def _exists(local: datetime) -> bool:
    """Return whether the wall time exists in its zone (clocks going forward skip some)."""
    back = local.astimezone(UTC).astimezone(local.tzinfo)
    return back.replace(tzinfo=None) == local.replace(tzinfo=None)


def wall_instant(day: date, at: time, tz: tzinfo) -> datetime:
    """Return the UTC instant at which the wall time `at` is reached on `day` in `tz`.

    A time that does not exist (clocks go forward) is reached at the first existing minute after
    the gap; a time that occurs twice (clocks go back) is reached at its first occurrence.
    """
    naive = datetime.combine(day, at)
    local = naive.replace(tzinfo=tz)
    for _ in range(MAX_GAP_MINUTES):
        if _exists(local):
            break
        naive += timedelta(minutes=1)
        local = naive.replace(tzinfo=tz)
    return local.astimezone(UTC)


def next_wall_run(after: datetime, rule: DateRule, at: time, tz: tzinfo) -> datetime | None:
    """Return the first run strictly after `after` on a date of `rule`, or None if it has ended."""
    cursor = after.astimezone(tz).date() - 2 * DAY
    for _ in range(CANDIDATE_DATES):
        day = rule.next_date(cursor)
        if day is None:
            return None
        instant = wall_instant(day, at, tz)
        if instant > after:
            return instant
        cursor = day
    return None


def previous_wall_run(before: datetime, rule: DateRule, at: time, tz: tzinfo) -> datetime | None:
    """Return the last run at or before `before` on a date of `rule`, or None if there is none."""
    cursor = before.astimezone(tz).date() + DAY
    for _ in range(CANDIDATE_DATES):
        day = rule.previous_date(cursor)
        if day is None:
            return None
        instant = wall_instant(day, at, tz)
        if instant <= before:
            return instant
        cursor = day - DAY
    return None

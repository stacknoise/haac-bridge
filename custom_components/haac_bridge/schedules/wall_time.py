"""Next and previous run of a fixed wall-clock time with weekdays, DST-safe (concept 19.3 step 4).

This module needs only the standard library, so the time arithmetic can be tested on its own.
HA's `find_next_time_expression_time` is not used: it skips the whole day when the wall time falls
into a DST gap, but a schedule must still run on that day.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import UTC, date, datetime, time, timedelta, tzinfo

SEARCH_DAYS = 9
"""Days to look at on each side; any non-empty weekday set matches within a week."""

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


def next_wall_run(after: datetime, days: Collection[int], at: time, tz: tzinfo) -> datetime | None:
    """Return the first run strictly after `after` on one of `days` (0 = Monday), or None."""
    start = after.astimezone(tz).date() - timedelta(days=1)
    for offset in range(SEARCH_DAYS + 1):
        day = start + timedelta(days=offset)
        if day.weekday() not in days:
            continue
        instant = wall_instant(day, at, tz)
        if instant > after:
            return instant
    return None


def previous_wall_run(
    before: datetime, days: Collection[int], at: time, tz: tzinfo
) -> datetime | None:
    """Return the last run at or before `before` on one of `days` (0 = Monday), or None."""
    start = before.astimezone(tz).date() + timedelta(days=1)
    for offset in range(SEARCH_DAYS + 1):
        day = start - timedelta(days=offset)
        if day.weekday() not in days:
            continue
        instant = wall_instant(day, at, tz)
        if instant <= before:
            return instant
    return None

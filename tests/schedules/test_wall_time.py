"""Tests for the DST-safe next and previous run of a wall-clock time (concept 19.3 step 4)."""

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from custom_components.haac_bridge.schedules.wall_time import (
    next_wall_run,
    previous_wall_run,
    wall_instant,
)

BERLIN = ZoneInfo("Europe/Berlin")
ALL_DAYS = frozenset(range(7))
WEEKDAYS = frozenset(range(5))


def utc(*args: int) -> datetime:
    """Return a UTC datetime."""
    return datetime(*args, tzinfo=UTC)


def local(moment: datetime | None) -> str | None:
    """Return a datetime as Berlin wall time with its abbreviation."""
    return None if moment is None else moment.astimezone(BERLIN).strftime("%Y-%m-%d %H:%M %Z")


def test_next_run_later_the_same_day() -> None:
    assert local(next_wall_run(utc(2026, 10, 5, 4, 0), ALL_DAYS, time(6, 45), BERLIN)) == (
        "2026-10-05 06:45 CEST"
    )


def test_next_run_is_strictly_after() -> None:
    first = next_wall_run(utc(2026, 10, 5, 4, 0), ALL_DAYS, time(6, 45), BERLIN)
    assert first is not None
    assert local(next_wall_run(first, ALL_DAYS, time(6, 45), BERLIN)) == "2026-10-06 06:45 CEST"


def test_next_run_skips_days_that_are_not_selected() -> None:
    friday_noon = utc(2026, 10, 9, 10, 0)
    assert local(next_wall_run(friday_noon, WEEKDAYS, time(6, 45), BERLIN)) == (
        "2026-10-12 06:45 CEST"
    )


def test_weekday_is_the_local_day() -> None:
    # 23:30 UTC on Sunday is already Monday 01:30 in Berlin.
    moment = utc(2026, 10, 4, 23, 30)
    assert local(next_wall_run(moment, frozenset({0}), time(2, 0), BERLIN)) == (
        "2026-10-05 02:00 CEST"
    )


def test_dst_gap_runs_at_the_first_minute_after_the_gap() -> None:
    # On 2026-03-29 the clocks jump from 02:00 to 03:00, so 02:30 does not exist.
    before = utc(2026, 3, 28, 12, 0)
    assert local(next_wall_run(before, ALL_DAYS, time(2, 30), BERLIN)) == "2026-03-29 03:00 CEST"


def test_dst_gap_runs_once_and_the_next_day_is_normal() -> None:
    gap_run = next_wall_run(utc(2026, 3, 28, 12, 0), ALL_DAYS, time(2, 30), BERLIN)
    assert gap_run is not None
    assert local(next_wall_run(gap_run, ALL_DAYS, time(2, 30), BERLIN)) == "2026-03-30 02:30 CEST"


def test_dst_gap_time_after_the_gap_is_unaffected() -> None:
    assert local(next_wall_run(utc(2026, 3, 28, 12, 0), ALL_DAYS, time(3, 30), BERLIN)) == (
        "2026-03-29 03:30 CEST"
    )


def test_dst_overlap_runs_at_the_first_occurrence_only() -> None:
    # On 2026-10-25 the clocks go back from 03:00 to 02:00, so 02:30 occurs twice.
    first = next_wall_run(utc(2026, 10, 24, 12, 0), ALL_DAYS, time(2, 30), BERLIN)
    assert first == utc(2026, 10, 25, 0, 30)
    second = next_wall_run(first, ALL_DAYS, time(2, 30), BERLIN)
    assert local(second) == "2026-10-26 02:30 CET"


def test_previous_run() -> None:
    monday_morning = utc(2026, 10, 12, 6, 0)
    assert local(previous_wall_run(monday_morning, WEEKDAYS, time(6, 45), BERLIN)) == (
        "2026-10-12 06:45 CEST"
    )
    sunday = utc(2026, 10, 11, 12, 0)
    assert local(previous_wall_run(sunday, WEEKDAYS, time(6, 45), BERLIN)) == (
        "2026-10-09 06:45 CEST"
    )


def test_previous_run_is_inclusive() -> None:
    moment = utc(2026, 10, 12, 4, 45)
    assert previous_wall_run(moment, WEEKDAYS, time(6, 45), BERLIN) == moment


def test_previous_run_in_a_dst_gap() -> None:
    assert local(previous_wall_run(utc(2026, 3, 29, 5, 0), ALL_DAYS, time(2, 30), BERLIN)) == (
        "2026-03-29 03:00 CEST"
    )


def test_wall_instant_in_utc_zone() -> None:
    assert wall_instant(datetime(2026, 3, 29).date(), time(2, 30), UTC) == utc(2026, 3, 29, 2, 30)

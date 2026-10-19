"""Tests for the date rules of one-off and repeating schedules (concept 19.10)."""

from datetime import date, timedelta

import pytest

from custom_components.haac_bridge.schedules.model import Repeat, RepeatFreq, parse_repeat
from custom_components.haac_bridge.schedules.recurrence import (
    DailyRule,
    DateRule,
    MonthlyRule,
    OnceRule,
    RecurrenceFactory,
    WeeklyRule,
    YearlyRule,
)

ALL_DAYS = frozenset(range(7))


def rule(freq: str, start: str | None, interval: int = 1, end: str | None = None, days=ALL_DAYS):
    """Return the date rule of a repeat with ISO dates."""
    raw: dict[str, object] = {"freq": freq, "interval": interval if freq != "once" else None}
    raw.update({"start_date": start, "end_date": end})
    return RecurrenceFactory().create(parse_repeat(raw), days)


def dates(rule_: DateRule, after: str, count: int) -> list[str]:
    """Return the next `count` dates after `after`."""
    found: list[str] = []
    cursor = date.fromisoformat(after)
    while len(found) < count and (nxt := rule_.next_date(cursor)) is not None:
        found.append(nxt.isoformat())
        cursor = nxt
    return found


def test_factory_picks_the_rule_by_frequency() -> None:
    factory = RecurrenceFactory()
    kinds = {
        RepeatFreq.ONCE: OnceRule,
        RepeatFreq.DAILY: DailyRule,
        RepeatFreq.WEEKLY: WeeklyRule,
        RepeatFreq.MONTHLY: MonthlyRule,
        RepeatFreq.YEARLY: YearlyRule,
    }
    for freq, kind in kinds.items():
        start = date(2026, 10, 26)
        assert isinstance(factory.create(Repeat(freq, 1, start), ALL_DAYS), kind)


def test_once_runs_exactly_on_its_date() -> None:
    once = rule("once", "2026-10-26")
    assert once.matches(date(2026, 10, 26))
    assert not once.matches(date(2026, 10, 27))
    assert once.next_date(date(2026, 10, 25)) == date(2026, 10, 26)
    assert once.next_date(date(2026, 10, 26)) is None
    assert once.previous_date(date(2026, 11, 30)) == date(2026, 10, 26)
    assert once.previous_date(date(2026, 10, 25)) is None


def test_daily_counts_days_from_the_start_date() -> None:
    every_third = rule("daily", "2026-10-05", 3)
    assert dates(every_third, "2026-10-04", 4) == [
        "2026-10-05",
        "2026-10-08",
        "2026-10-11",
        "2026-10-14",
    ]
    assert every_third.matches(date(2026, 10, 11))
    assert not every_third.matches(date(2026, 10, 12))


def test_a_later_start_date_delays_the_first_run() -> None:
    daily = rule("daily", "2026-11-01")
    assert daily.next_date(date(2026, 10, 1)) == date(2026, 11, 1)
    assert not daily.matches(date(2026, 10, 31))
    assert daily.previous_date(date(2026, 10, 31)) is None


def test_the_end_date_is_the_last_run_date() -> None:
    daily = rule("daily", "2026-10-05", 1, "2026-10-07")
    assert dates(daily, "2026-10-01", 9) == ["2026-10-05", "2026-10-06", "2026-10-07"]
    assert daily.previous_date(date(2026, 12, 1)) == date(2026, 10, 7)
    stepping = rule("daily", "2026-10-05", 5, "2026-10-14")
    assert dates(stepping, "2026-10-01", 9) == ["2026-10-05", "2026-10-10"]


def test_weekly_uses_the_chosen_weekdays_of_every_nth_week() -> None:
    # Start on a Wednesday; the first week is the one of 5 Oct. Monday and Thursday, every 2nd week.
    biweekly = rule("weekly", "2026-10-07", 2, days={0, 3})
    assert dates(biweekly, "2026-10-01", 4) == [
        "2026-10-08",
        "2026-10-19",
        "2026-10-22",
        "2026-11-02",
    ]
    assert not biweekly.matches(date(2026, 10, 5))  # Monday before the start date
    assert not biweekly.matches(date(2026, 10, 12))  # week 1 of 2


def test_weekly_counts_iso_weeks_across_the_year_change() -> None:
    biweekly = rule("weekly", "2026-12-28", 2, days={0})
    assert dates(biweekly, "2026-12-01", 3) == ["2026-12-28", "2027-01-11", "2027-01-25"]
    assert not biweekly.matches(date(2027, 1, 4))


def test_weekly_with_the_largest_interval() -> None:
    yearly_ish = rule("weekly", "2026-10-05", 52, days={0})
    assert yearly_ish.next_date(date(2026, 10, 5)) == date(2027, 10, 4)


def test_monthly_runs_on_the_day_of_month_of_the_start_date() -> None:
    monthly = rule("monthly", "2026-10-15")
    assert dates(monthly, "2026-10-01", 3) == ["2026-10-15", "2026-11-15", "2026-12-15"]
    assert monthly.previous_date(date(2026, 12, 14)) == date(2026, 11, 15)


def test_monthly_uses_the_last_day_of_a_shorter_month() -> None:
    monthly = rule("monthly", "2027-01-31")
    assert dates(monthly, "2027-01-01", 5) == [
        "2027-01-31",
        "2027-02-28",
        "2027-03-31",
        "2027-04-30",
        "2027-05-31",
    ]
    leap = rule("monthly", "2027-12-31")
    assert dates(leap, "2027-12-31", 2) == ["2028-01-31", "2028-02-29"]


def test_monthly_interval_counts_months_from_the_start_date() -> None:
    quarterly = rule("monthly", "2026-11-30", 3)
    assert dates(quarterly, "2026-11-01", 3) == ["2026-11-30", "2027-02-28", "2027-05-30"]
    yearly_ish = rule("monthly", "2026-10-15", 12)
    assert yearly_ish.next_date(date(2026, 10, 15)) == date(2027, 10, 15)


def test_yearly_runs_on_the_day_and_month_of_the_start_date() -> None:
    yearly = rule("yearly", "2026-05-01")
    assert dates(yearly, "2026-01-01", 3) == ["2026-05-01", "2027-05-01", "2028-05-01"]
    assert yearly.matches(date(2030, 5, 1))
    assert not yearly.matches(date(2030, 5, 2))


def test_yearly_29_february_runs_on_28_february_in_other_years() -> None:
    leap = rule("yearly", "2028-02-29")
    assert dates(leap, "2028-01-01", 5) == [
        "2028-02-29",
        "2029-02-28",
        "2030-02-28",
        "2031-02-28",
        "2032-02-29",
    ]
    assert leap.previous_date(date(2030, 6, 1)) == date(2030, 2, 28)


def test_next_date_never_goes_back_before_the_start() -> None:
    yearly = rule("yearly", "2030-05-01")
    assert yearly.next_date(date(2026, 1, 1)) == date(2030, 5, 1)


def test_the_calendar_ends_without_an_error() -> None:
    last = rule("yearly", "9998-05-01", end="9999-12-31")
    assert last.next_date(date(9998, 5, 1)) == date(9999, 5, 1)
    assert last.next_date(date(9999, 5, 1)) is None
    assert rule("daily", "9999-12-30").next_date(date(9999, 12, 31)) is None


def test_the_end_date_has_no_upper_limit() -> None:
    far = rule("monthly", "2026-10-15", end="2126-10-15")
    assert far.next_date(date(2026, 10, 15)) == date(2026, 11, 15)
    assert far.matches(date(2126, 10, 15))
    assert far.next_date(date(2126, 10, 15)) is None


@pytest.mark.parametrize(
    ("freq", "interval"), [("daily", 365), ("weekly", 52), ("monthly", 12), ("yearly", 1)]
)
def test_next_and_previous_date_find_each_other_with_the_largest_interval(
    freq: str, interval: int
) -> None:
    repeating = rule(freq, "2026-10-05", interval, days={0})
    following = repeating.next_date(date(2026, 10, 5))
    assert following is not None
    assert following - date(2026, 10, 5) <= timedelta(days=366)
    assert repeating.previous_date(following) == following
    assert repeating.previous_date(following - timedelta(days=1)) == date(2026, 10, 5)

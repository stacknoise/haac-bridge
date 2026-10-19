"""Trigger planners: when a schedule runs next and last ran (concept 19.3, 18.2 TriggerFactory)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta, tzinfo
from typing import Protocol

from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.util import dt as dt_util

from ..const import NEXT_RUNS_COUNT
from ..core.errors import ErrorCode, ScheduleError
from .model import Repeat, When, WhenType
from .recurrence import DateRule, RecurrenceFactory
from .wall_time import next_wall_run, previous_wall_run

SUN_SEARCH_DAYS = 368
"""Days a sun trigger looks ahead or back for an event before it gives up (concept 19.3 step 5).

A year plus the days around it, so a yearly schedule is found from any day."""


class Trigger(Protocol):
    """Computes the runs of one schedule; None means no run can be computed."""

    def next_run(self, after: datetime) -> datetime | None:
        """Return the first run strictly after `after` (UTC), or None."""

    def previous_run(self, before: datetime) -> datetime | None:
        """Return the last run at or before `before` (UTC), or None."""


class TimeTrigger:
    """A fixed wall-clock time on the dates of a rule."""

    def __init__(self, when: When, rule: DateRule, tz: tzinfo) -> None:
        """Remember the time, the date rule and the time zone of the planning."""
        if when.time is None:
            raise ScheduleError(ErrorCode.SCH_INVALID)
        self._rule = rule
        self._at = when.time
        self._tz = tz

    def next_run(self, after: datetime) -> datetime | None:
        """Return the first run after `after`, DST-safe."""
        return next_wall_run(after, self._rule, self._at, self._tz)

    def previous_run(self, before: datetime) -> datetime | None:
        """Return the last run at or before `before`, DST-safe."""
        return previous_wall_run(before, self._rule, self._at, self._tz)


class SunTrigger:
    """Sunrise or sunset plus an offset, on the dates of a rule, by the local date of the result."""

    def __init__(
        self, hass: HomeAssistant, when: When, rule: DateRule, event: str, tz: tzinfo
    ) -> None:
        """Remember the sun event, the offset, the date rule and the time zone."""
        self._hass = hass
        self._rule = rule
        self._event = event
        self._offset = timedelta(minutes=when.offset_min)
        self._tz = tz

    def _instant(self, day_offset: int, today: datetime) -> datetime | None:
        """Return the run on the sun event of `today` plus `day_offset` days, or None."""
        day = today + timedelta(days=day_offset)
        if not self._near_run_date(day.astimezone(self._tz).date()):
            return None
        event = get_astral_event_date(self._hass, self._event, day)
        if event is None:
            return None
        instant = event + self._offset
        if not self._rule.matches(instant.astimezone(self._tz).date()):
            return None
        return instant

    def _near_run_date(self, day: date) -> bool:
        """Return whether the rule runs on `day` or a day next to it, so the sun need not be computed."""
        return any(self._rule.matches(day + timedelta(days=step)) for step in (-1, 0, 1))

    def next_run(self, after: datetime) -> datetime | None:
        """Return the first run after `after`; None if the sun never gives one within a year."""
        for day_offset in range(-1, SUN_SEARCH_DAYS):
            instant = self._instant(day_offset, after)
            if instant is not None and instant > after:
                return instant
        return None

    def previous_run(self, before: datetime) -> datetime | None:
        """Return the last run at or before `before`; None if there is none within a year."""
        for day_offset in range(1, -SUN_SEARCH_DAYS, -1):
            instant = self._instant(day_offset, before)
            if instant is not None and instant <= before:
                return instant
        return None


class TriggerFactory:
    """Creates the trigger planner that belongs to a schedule's `when` and `repeat` (concept 18.2)."""

    def __init__(self, hass: HomeAssistant, recurrence: RecurrenceFactory | None = None) -> None:
        """Remember hass for the sun calculations and the factory of the date rules."""
        self._hass = hass
        self._recurrence = recurrence or RecurrenceFactory()

    def create(self, when: When, repeat: Repeat | None = None) -> Trigger:
        """Return the planner for this trigger, bound to the current HA time zone.

        Without `repeat` the schedule runs weekly on the weekdays of `when`.
        """
        tz = dt_util.get_default_time_zone()
        rule = self._recurrence.create(repeat or Repeat(), when.days)
        builders: dict[WhenType, Callable[[], Trigger]] = {
            WhenType.TIME: lambda: TimeTrigger(when, rule, tz),
            WhenType.SUNRISE: lambda: SunTrigger(self._hass, when, rule, SUN_EVENT_SUNRISE, tz),
            WhenType.SUNSET: lambda: SunTrigger(self._hass, when, rule, SUN_EVENT_SUNSET, tz),
        }
        return builders[when.type]()

    def upcoming(
        self, when: When, repeat: Repeat, after: datetime, count: int = NEXT_RUNS_COUNT
    ) -> list[datetime]:
        """Return up to `count` runs after `after`, in order (concept 19.10 `next_runs`)."""
        trigger = self.create(when, repeat)
        runs: list[datetime] = []
        while len(runs) < count and (found := trigger.next_run(runs[-1] if runs else after)):
            runs.append(found)
        return runs

    def is_ended(self, when: When, repeat: Repeat, after: datetime) -> bool:
        """Return whether the schedule has no run left after `after`, as the rule ends (concept 19.10).

        A sun schedule without an event within a year is not ended: its rule still has dates.
        """
        if self.create(when, repeat).next_run(after) is not None:
            return False
        today = after.astimezone(dt_util.get_default_time_zone()).date()
        return self._recurrence.create(repeat, when.days).next_date(today) is None

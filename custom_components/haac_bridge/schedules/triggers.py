"""Trigger planners: when a schedule runs next and last ran (concept 19.3, 18.2 TriggerFactory)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, tzinfo
from typing import Protocol

from homeassistant.const import SUN_EVENT_SUNRISE, SUN_EVENT_SUNSET
from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.util import dt as dt_util

from ..core.errors import ErrorCode, ScheduleError
from .model import When, WhenType
from .wall_time import next_wall_run, previous_wall_run

SUN_SEARCH_DAYS = 366
"""Days a sun trigger looks ahead or back for an event before it gives up (concept 19.3 step 5)."""


class Trigger(Protocol):
    """Computes the runs of one schedule; None means no run can be computed."""

    def next_run(self, after: datetime) -> datetime | None:
        """Return the first run strictly after `after` (UTC), or None."""

    def previous_run(self, before: datetime) -> datetime | None:
        """Return the last run at or before `before` (UTC), or None."""


class TimeTrigger:
    """A fixed wall-clock time on some weekdays."""

    def __init__(self, when: When, tz: tzinfo) -> None:
        """Remember the time, the weekdays and the time zone of the planning."""
        if when.time is None:
            raise ScheduleError(ErrorCode.SCH_INVALID)
        self._when = when
        self._at = when.time
        self._tz = tz

    def next_run(self, after: datetime) -> datetime | None:
        """Return the first run after `after`, DST-safe."""
        return next_wall_run(after, self._when.days, self._at, self._tz)

    def previous_run(self, before: datetime) -> datetime | None:
        """Return the last run at or before `before`, DST-safe."""
        return previous_wall_run(before, self._when.days, self._at, self._tz)


class SunTrigger:
    """Sunrise or sunset plus an offset, on some weekdays of the local date of the result."""

    def __init__(self, hass: HomeAssistant, when: When, event: str, tz: tzinfo) -> None:
        """Remember the sun event, the offset, the weekdays and the time zone."""
        self._hass = hass
        self._when = when
        self._event = event
        self._offset = timedelta(minutes=when.offset_min)
        self._tz = tz

    def _instant(self, day_offset: int, today: datetime) -> datetime | None:
        """Return the run on the sun event of `today` plus `day_offset` days, or None."""
        event = get_astral_event_date(self._hass, self._event, today + timedelta(days=day_offset))
        if event is None:
            return None
        instant = event + self._offset
        if instant.astimezone(self._tz).weekday() not in self._when.days:
            return None
        return instant

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
    """Creates the trigger planner that belongs to a schedule's `when` (concept 18.2)."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Remember hass for the sun calculations."""
        self._hass = hass

    def create(self, when: When) -> Trigger:
        """Return the planner for this trigger, bound to the current HA time zone."""
        tz = dt_util.get_default_time_zone()
        builders: dict[WhenType, Callable[[], Trigger]] = {
            WhenType.TIME: lambda: TimeTrigger(when, tz),
            WhenType.SUNRISE: lambda: SunTrigger(self._hass, when, SUN_EVENT_SUNRISE, tz),
            WhenType.SUNSET: lambda: SunTrigger(self._hass, when, SUN_EVENT_SUNSET, tz),
        }
        return builders[when.type]()

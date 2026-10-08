"""Plans the next run of every schedule and calls the runner when one is due (concept 19.3)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from homeassistant.const import EVENT_CORE_CONFIG_UPDATE
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

from ..const import MISSED_RUN_GRACE
from .model import Paused, PauseReason, Schedule
from .store import ScheduleStore
from .triggers import TriggerFactory


class SchedulePlanner:
    """Keeps one timer per active schedule and re-plans after every run and every time change."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: ScheduleStore,
        triggers: TriggerFactory,
        on_due: Callable[[str], Awaitable[None]],
        on_changed: Callable[[str], None],
    ) -> None:
        """Create the planner; `on_due` runs a schedule, `on_changed` reports a pause or resume."""
        self._hass = hass
        self._store = store
        self._triggers = triggers
        self._on_due = on_due
        self._on_changed = on_changed
        self._unsubs: dict[str, CALLBACK_TYPE] = {}
        self._planned: dict[str, datetime] = {}
        self._unsub_config: CALLBACK_TYPE | None = None

    async def async_start(self) -> None:
        """Plan every schedule, follow time zone and location changes and catch up missed runs."""
        await self.async_plan_all()
        self._unsub_config = self._hass.bus.async_listen(
            EVENT_CORE_CONFIG_UPDATE, self._handle_config_update
        )
        now = dt_util.utcnow()
        for schedule in self._store.schedules:
            if schedule.id in self._unsubs and self._missed(schedule, now):
                self._hass.async_create_task(self._on_due(schedule.id))

    @callback
    def async_stop(self) -> None:
        """Cancel every timer and stop following configuration changes."""
        for schedule_id in list(self._unsubs):
            self._cancel(schedule_id)
        if self._unsub_config is not None:
            self._unsub_config()
            self._unsub_config = None

    async def async_plan_all(self) -> None:
        """Plan every schedule anew."""
        for schedule in self._store.schedules:
            await self.async_plan(schedule.id)

    async def async_plan(self, schedule_id: str, after: datetime | None = None) -> None:
        """Plan the next run of one schedule, or cancel its timer if it is not active."""
        self._cancel(schedule_id)
        schedule = self._store.get(schedule_id)
        if schedule is None or not self._plannable(schedule):
            return
        next_run = self._triggers.create(schedule.when).next_run(after or dt_util.utcnow())
        if next_run is None:
            await self._async_set_sun_pause(schedule, paused=True)
            return
        if schedule.paused is not None:
            await self._async_set_sun_pause(schedule, paused=False)
        self._planned[schedule_id] = next_run
        self._unsubs[schedule_id] = async_track_point_in_utc_time(
            self._hass, self._make_job(schedule_id), next_run
        )

    def planned_run(self, schedule_id: str) -> datetime | None:
        """Return when the schedule runs next, or None if it is not planned."""
        return self._planned.get(schedule_id)

    def _cancel(self, schedule_id: str) -> None:
        """Cancel the timer of one schedule."""
        self._planned.pop(schedule_id, None)
        if (unsub := self._unsubs.pop(schedule_id, None)) is not None:
            unsub()

    @staticmethod
    def _plannable(schedule: Schedule) -> bool:
        """Return whether a timer is needed: enabled, and not paused for a reason a timer cannot fix."""
        paused = schedule.paused
        return schedule.enabled and (paused is None or paused.reason is PauseReason.SUN_UNAVAILABLE)

    def _make_job(self, schedule_id: str) -> Callable[[datetime], Awaitable[None]]:
        """Return the timer callback of one schedule."""

        async def _fire(_now: datetime) -> None:
            """Plan the next run first, so a failing run never stops the schedule, then run."""
            planned = self._planned.get(schedule_id)
            self._unsubs.pop(schedule_id, None)
            after = dt_util.utcnow()
            if planned is not None:
                after = max(after, planned + timedelta(seconds=1))
            await self.async_plan(schedule_id, after)
            await self._on_due(schedule_id)

        return _fire

    async def _async_set_sun_pause(self, schedule: Schedule, *, paused: bool) -> None:
        """Pause a sun schedule that has no event, or resume one whose event is back."""
        is_paused = schedule.paused is not None
        if paused == is_paused:
            return
        new_pause = Paused(PauseReason.SUN_UNAVAILABLE, dt_util.utcnow()) if paused else None
        await self._store.async_replace(schedule.with_changes(paused=new_pause))
        self._on_changed(schedule.id)

    def _missed(self, schedule: Schedule, now: datetime) -> bool:
        """Return whether a run was due shortly before `now` and has not happened (concept 19.3)."""
        previous = self._triggers.create(schedule.when).previous_run(now)
        if previous is None or now - previous > MISSED_RUN_GRACE or schedule.created_at > previous:
            return False
        return schedule.last_run is None or schedule.last_run.at < previous

    @callback
    def _handle_config_update(self, _event: Event) -> None:
        """Re-plan everything after a change of the time zone or the location."""
        self._hass.async_create_task(self.async_plan_all())

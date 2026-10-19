"""Plans the next run of every schedule and calls the runner when one is due (concept 19.3)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from homeassistant.const import EVENT_CORE_CONFIG_UPDATE
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

from ..const import MISSED_RUN_GRACE, NEXT_RUNS_COUNT
from .model import (
    Paused,
    PauseReason,
    RepeatFreq,
    Schedule,
    check_repeat,
    parse_repeat,
    parse_when,
)
from .store import ScheduleStore
from .triggers import Trigger, TriggerFactory


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
        """Create the planner.

        `on_due` runs a schedule and `on_changed` reports a new planned time or pause.
        The manager sets `on_missed` to be told about a run HA missed (concept 19.10, 19.11).
        """
        self._hass = hass
        self._store = store
        self._triggers = triggers
        self._on_due = on_due
        self._on_changed = on_changed
        self.on_missed: Callable[..., Awaitable[None]] | None = None
        self._unsubs: dict[str, CALLBACK_TYPE] = {}
        self._planned: dict[str, datetime] = {}
        self._ended: set[str] = set()
        self._unsub_config: CALLBACK_TYPE | None = None

    async def async_start(self) -> None:
        """Plan every schedule, follow time zone and location changes and catch up missed runs."""
        await self.async_plan_all()
        self._unsub_config = self._hass.bus.async_listen(
            EVENT_CORE_CONFIG_UPDATE, self._handle_config_update
        )
        now = dt_util.utcnow()
        for schedule in list(self._store.schedules):
            if schedule.id not in self._unsubs and schedule.id not in self._ended:
                continue
            if self._missed(schedule, now):
                self._hass.async_create_task(self._on_due(schedule.id))
            else:
                await self._async_report_missed(schedule, now)

    async def _async_report_missed(self, schedule: Schedule, now: datetime) -> None:
        """Tell `on_missed` about the last planned run that HA missed by more than the grace.

        It counts if it fell after the last change of the schedule and no run followed it. The
        run is the last one of the schedule if the planner found no later date (concept 19.10).
        """
        previous = self._trigger(schedule).previous_run(now)
        if (
            self.on_missed is not None
            and previous is not None
            and schedule.updated_at <= previous
            and (schedule.last_run is None or schedule.last_run.at < previous)
        ):
            await self.on_missed(schedule, previous, last=schedule.id in self._ended)

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
        """Plan the next run of one schedule, or cancel its timer if it is not active.

        A changed planned time is reported, so sensors and subscribers follow a re-plan after the
        start or after a time zone or location change (review findings 1 and 2).
        """
        previous = self._planned.get(schedule_id)
        await self._async_plan(schedule_id, after)
        if self._planned.get(schedule_id) != previous:
            self._on_changed(schedule_id)

    async def _async_plan(self, schedule_id: str, after: datetime | None) -> None:
        """Replace the timer of one schedule by one for its next run, if it needs one."""
        self._cancel(schedule_id)
        schedule = self._store.get(schedule_id)
        if schedule is None or not self._plannable(schedule):
            return
        reference = after or dt_util.utcnow()
        next_run = self._trigger(schedule).next_run(reference)
        if next_run is None:
            if self._triggers.is_ended(schedule.when, schedule.repeat, reference):
                self._ended.add(schedule_id)
            else:
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

    def ends_with_run(self, schedule_id: str) -> bool:
        """Return whether the run that is due now is the last one of the schedule (concept 19.10).

        True after the planner found no further date for an enabled, active schedule: the run of a
        one-off schedule or of one that reached its end date, which removes the schedule.
        """
        return schedule_id in self._ended

    def next_runs(self, schedule: Schedule) -> list[datetime]:
        """Return the next runs of a planned schedule, none if it is disabled, paused or expired."""
        if schedule.id not in self._planned:
            return []
        return self._triggers.upcoming(
            schedule.when, schedule.repeat, dt_util.utcnow(), NEXT_RUNS_COUNT
        )

    def is_expired(self, schedule: Schedule) -> bool:
        """Return whether the schedule has no date left, e.g. a one-off in the past (concept 19.10)."""
        return self._triggers.is_ended(schedule.when, schedule.repeat, dt_util.utcnow())

    def preview(self, raw_when: object, raw_repeat: object) -> list[datetime]:
        """Return the next runs of a draft that is not saved, or raise HAB-SCH-001 / HAB-SCH-009."""
        now = dt_util.utcnow()
        repeat = parse_repeat(raw_repeat, dt_util.as_local(now).date())
        when = parse_when(raw_when, days_required=repeat.freq is RepeatFreq.WEEKLY)
        if raw_repeat is not None:
            check_repeat(repeat, when, now)
        return self._triggers.upcoming(when, repeat, now, NEXT_RUNS_COUNT)

    def _trigger(self, schedule: Schedule) -> Trigger:
        """Return the trigger of a schedule for its time and its date rule."""
        return self._triggers.create(schedule.when, schedule.repeat)

    def _cancel(self, schedule_id: str) -> None:
        """Cancel the timer of one schedule."""
        self._planned.pop(schedule_id, None)
        self._ended.discard(schedule_id)
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
        await self._store.async_replace(schedule.with_changes(paused=new_pause), delay=True)
        self._on_changed(schedule.id)

    def _missed(self, schedule: Schedule, now: datetime) -> bool:
        """Return whether a run was due shortly before `now` and has not happened (concept 19.3)."""
        previous = self._trigger(schedule).previous_run(now)
        if previous is None or now - previous > MISSED_RUN_GRACE or schedule.created_at > previous:
            return False
        return schedule.last_run is None or schedule.last_run.at < previous

    @callback
    def _handle_config_update(self, _event: Event) -> None:
        """Re-plan everything after a change of the time zone or the location."""
        self._hass.async_create_task(self.async_plan_all())

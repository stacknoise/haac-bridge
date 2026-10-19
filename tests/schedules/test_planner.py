"""Tests for the schedule planner: timers, re-planning and missed runs (concept 19.3)."""

from datetime import date
from typing import Any
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.haac_bridge.schedules.model import (
    LastRun,
    Paused,
    PauseReason,
    Repeat,
    RepeatFreq,
    RunResult,
    Schedule,
)
from custom_components.haac_bridge.schedules.planner import SchedulePlanner
from custom_components.haac_bridge.schedules.store import ScheduleStore
from custom_components.haac_bridge.schedules.triggers import TriggerFactory

from .conftest import ALL_DAYS, make_schedule, utc

SUN_FUNCTION = "custom_components.haac_bridge.schedules.triggers.get_astral_event_date"
SUNRISE = {"type": "sunrise", "days": ALL_DAYS}


class Harness:
    """A planner with a store, a recording runner and a change counter."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Create the store and the planner."""
        self.store = ScheduleStore(hass)
        self.calls: list[str] = []
        self.changes = 0
        self.changed_ids: list[str] = []
        self.missed: list[tuple[str, Any, bool]] = []
        self.planner = SchedulePlanner(
            hass, self.store, TriggerFactory(hass), self._run, self._changed
        )
        self.planner.on_missed = self._missed

    async def _run(self, schedule_id: str) -> None:
        """Record a due run."""
        self.calls.append(schedule_id)

    async def _missed(self, schedule: Schedule, at: Any, *, last: bool) -> None:
        """Record a run that HA missed."""
        self.missed.append((schedule.id, at, last))

    def _changed(self, schedule_id: str) -> None:
        """Count a new planned time, a pause or a resume."""
        assert schedule_id
        self.changed_ids.append(schedule_id)
        self.changes += 1

    async def start(self, hass: HomeAssistant, *schedules: Schedule) -> None:
        """Load the store, add the schedules and start the planner."""
        await self.store.async_load()
        for schedule in schedules:
            await self.store.async_add(schedule)
        await self.planner.async_start()
        await hass.async_block_till_done()


async def _fire(hass: HomeAssistant, freezer: FrozenDateTimeFactory, moment: str) -> None:
    """Move the clock to `moment` and let the due timers run."""
    freezer.move_to(moment)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("berlin")
async def test_plans_and_fires_the_next_run(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = make_schedule()
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.planner.planned_run(schedule.id) == utc(2026, 10, 5, 5, 45)

    await _fire(hass, freezer, "2026-10-05 05:45:01+00:00")
    assert harness.calls == [schedule.id]
    assert harness.planner.planned_run(schedule.id) == utc(2026, 10, 6, 5, 45)

    await _fire(hass, freezer, "2026-10-06 05:45:01+00:00")
    assert harness.calls == [schedule.id, schedule.id]
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_weekdays_only(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to("2026-10-09 10:00:00+00:00")  # Friday
    schedule = make_schedule({"type": "time", "time": "07:45", "days": [0, 1, 2, 3, 4]})
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.planner.planned_run(schedule.id) == utc(2026, 10, 12, 5, 45)  # Monday
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_disabled_and_paused_schedules_are_not_planned(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    off = make_schedule(enabled=False)
    paused = make_schedule(paused=Paused(PauseReason.NO_ENTITIES, utc(2026, 10, 1)))
    harness = Harness(hass)
    await harness.start(hass, off, paused)
    assert harness.planner.planned_run(off.id) is None
    assert harness.planner.planned_run(paused.id) is None

    await _fire(hass, freezer, "2026-10-05 05:45:01+00:00")
    assert harness.calls == []
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_replanning_after_a_change_cancels_the_old_timer(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = make_schedule()
    harness = Harness(hass)
    await harness.start(hass, schedule)

    await harness.store.async_replace(schedule.with_changes(enabled=False))
    await harness.planner.async_plan(schedule.id)
    assert harness.planner.planned_run(schedule.id) is None

    await _fire(hass, freezer, "2026-10-05 05:45:01+00:00")
    assert harness.calls == []
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_removed_schedule_is_unplanned(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = make_schedule()
    harness = Harness(hass)
    await harness.start(hass, schedule)

    await harness.store.async_remove([schedule.id])
    await harness.planner.async_plan(schedule.id)
    await _fire(hass, freezer, "2026-10-05 05:45:01+00:00")
    assert harness.calls == []
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_stop_cancels_all_timers(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = make_schedule()
    harness = Harness(hass)
    await harness.start(hass, schedule)

    harness.planner.async_stop()
    await _fire(hass, freezer, "2026-10-05 05:45:01+00:00")
    assert harness.calls == []
    assert harness.planner.planned_run(schedule.id) is None


@pytest.mark.usefixtures("berlin")
async def test_time_zone_change_replans(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = make_schedule()
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.planner.planned_run(schedule.id) == utc(2026, 10, 5, 5, 45)

    await hass.config.async_update(time_zone="Asia/Tokyo")
    await hass.async_block_till_done()
    assert harness.planner.planned_run(schedule.id) == utc(2026, 10, 5, 22, 45)
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_a_new_planned_time_is_reported(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = make_schedule()
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.changed_ids == [schedule.id]  # planned for the first time

    await harness.planner.async_plan_all()
    assert harness.changed_ids == [schedule.id]  # same time again: nothing to report

    await hass.config.async_update(time_zone="Asia/Tokyo")
    await hass.async_block_till_done()
    assert harness.changed_ids == [schedule.id] * 2  # time zone change moved the run
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_cancelling_a_plan_is_reported(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = make_schedule()
    harness = Harness(hass)
    await harness.start(hass, schedule)
    await harness.store.async_replace(schedule.with_changes(enabled=False))
    await harness.planner.async_plan(schedule.id)
    assert harness.planner.planned_run(schedule.id) is None
    assert harness.changed_ids == [schedule.id] * 2
    harness.planner.async_stop()


@pytest.mark.parametrize(
    ("now", "extra", "runs"),
    [
        ("2026-10-05 05:48:00+00:00", {}, 1),  # 3 minutes late: carried out once
        ("2026-10-05 05:50:00+00:00", {}, 1),  # exactly 5 minutes late: still carried out
        ("2026-10-05 05:51:00+00:00", {}, 0),  # 6 minutes late: skipped
        (
            "2026-10-05 05:48:00+00:00",
            {"last_run": LastRun(utc(2026, 10, 5, 5, 45, 5), RunResult.OK)},
            0,  # it did run
        ),
        (
            "2026-10-05 05:48:00+00:00",
            {"last_run": LastRun(utc(2026, 10, 4, 5, 45, 5), RunResult.OK)},
            1,  # the last run was yesterday
        ),
        ("2026-10-05 05:48:00+00:00", {"created_at": utc(2026, 10, 5, 5, 46)}, 0),  # too new
        ("2026-10-05 05:48:00+00:00", {"enabled": False}, 0),
    ],
)
@pytest.mark.usefixtures("berlin")
async def test_missed_run_policy(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    now: str,
    extra: dict[str, Any],
    runs: int,
) -> None:
    freezer.move_to(now)
    schedule = make_schedule(**extra)
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.calls == [schedule.id] * runs
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_sun_schedule_without_event_is_paused_and_resumes(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = make_schedule(SUNRISE)
    harness = Harness(hass)
    with patch(SUN_FUNCTION, return_value=None):
        await harness.start(hass, schedule)
    stored = harness.store.get(schedule.id)
    assert stored is not None
    assert stored.paused is not None
    assert stored.paused.reason is PauseReason.SUN_UNAVAILABLE
    assert harness.planner.planned_run(schedule.id) is None
    assert harness.changes == 1  # the pause; the planned time stays empty

    await harness.planner.async_plan_all()
    resumed = harness.store.get(schedule.id)
    assert resumed is not None
    assert resumed.paused is None
    assert harness.planner.planned_run(schedule.id) is not None
    assert harness.changes == 3  # the resume and the new planned time
    harness.planner.async_stop()


def _repeating(
    freq: str, start: str, interval: int = 1, end: str | None = None, **changes: Any
) -> Schedule:
    """Return a schedule at 07:45 with a date rule."""
    repeat = Repeat(
        RepeatFreq(freq),
        1 if freq == "once" else interval,
        date.fromisoformat(start),
        None if end is None else date.fromisoformat(end),
    )
    when = {"type": "time", "time": "07:45", "days": ALL_DAYS}
    return make_schedule(when, repeat=repeat, **changes)


@pytest.mark.usefixtures("berlin")
async def test_plans_by_the_date_rule(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    every_third_day = _repeating("daily", "2026-10-04", 3)
    monthly = _repeating("monthly", "2026-10-31")
    later = _repeating("weekly", "2026-11-02", 2)
    harness = Harness(hass)
    await harness.start(hass, every_third_day, monthly, later)
    assert harness.planner.planned_run(every_third_day.id) == utc(2026, 10, 7, 5, 45)
    assert harness.planner.planned_run(monthly.id) == utc(2026, 10, 31, 6, 45)
    assert harness.planner.planned_run(later.id) == utc(2026, 11, 2, 6, 45)
    assert harness.planner.next_runs(every_third_day) == [
        utc(2026, 10, 7, 5, 45),
        utc(2026, 10, 10, 5, 45),
        utc(2026, 10, 13, 5, 45),
    ]
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_a_one_off_run_is_the_last_one(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = _repeating("once", "2026-10-06")
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.planner.planned_run(schedule.id) == utc(2026, 10, 6, 5, 45)
    assert not harness.planner.ends_with_run(schedule.id)

    await _fire(hass, freezer, "2026-10-06 05:45:01+00:00")
    assert harness.calls == [schedule.id]
    assert harness.planner.planned_run(schedule.id) is None
    assert harness.planner.ends_with_run(schedule.id)
    assert harness.planner.next_runs(schedule) == []
    assert harness.planner.is_expired(schedule)
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_the_run_on_the_end_date_is_the_last_one(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-05 05:00:00+00:00")
    schedule = _repeating("daily", "2026-10-05", end="2026-10-06")
    harness = Harness(hass)
    await harness.start(hass, schedule)

    await _fire(hass, freezer, "2026-10-05 05:45:01+00:00")
    assert harness.planner.planned_run(schedule.id) == utc(2026, 10, 6, 5, 45)
    assert not harness.planner.ends_with_run(schedule.id)
    assert not harness.planner.is_expired(schedule)

    await _fire(hass, freezer, "2026-10-06 05:45:01+00:00")
    assert harness.calls == [schedule.id] * 2
    assert harness.planner.ends_with_run(schedule.id)
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_a_disabled_one_off_in_the_past_is_expired_and_not_planned(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-07 05:00:00+00:00")
    schedule = _repeating("once", "2026-10-06", enabled=False)
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.planner.planned_run(schedule.id) is None
    assert not harness.planner.ends_with_run(schedule.id)
    assert harness.planner.is_expired(schedule)
    assert harness.calls == []
    assert harness.missed == []  # a disabled schedule did not miss anything
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_a_run_within_the_grace_is_made_up_also_for_the_last_run(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-06 05:47:00+00:00")  # two minutes after the planned run
    schedule = _repeating("once", "2026-10-06")
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.calls == [schedule.id]
    assert harness.planner.ends_with_run(schedule.id)
    assert harness.missed == []
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_a_last_run_missed_beyond_the_grace_is_reported_as_the_last(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-06 07:00:00+00:00")  # 75 minutes late
    schedule = _repeating("once", "2026-10-06")
    harness = Harness(hass)
    await harness.start(hass, schedule)
    assert harness.calls == []
    assert harness.missed == [(schedule.id, utc(2026, 10, 6, 5, 45), True)]
    harness.planner.async_stop()


@pytest.mark.usefixtures("berlin")
async def test_a_run_missed_beyond_the_grace_is_reported_for_a_repeating_schedule(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-06 07:00:00+00:00")
    missed = _repeating("daily", "2026-10-01")
    ran = _repeating(
        "daily", "2026-10-01", last_run=LastRun(utc(2026, 10, 6, 5, 45, 3), RunResult.OK)
    )
    changed_later = _repeating("daily", "2026-10-01", updated_at=utc(2026, 10, 6, 6, 0))
    harness = Harness(hass)
    await harness.start(hass, missed, ran, changed_later)
    assert harness.calls == []
    assert harness.missed == [(missed.id, utc(2026, 10, 6, 5, 45), False)]
    harness.planner.async_stop()

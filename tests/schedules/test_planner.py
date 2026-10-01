"""Tests for the schedule planner: timers, re-planning and missed runs (concept 19.3)."""

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
        self.planner = SchedulePlanner(
            hass, self.store, TriggerFactory(hass), self._run, self._changed
        )

    async def _run(self, schedule_id: str) -> None:
        """Record a due run."""
        self.calls.append(schedule_id)

    def _changed(self) -> None:
        """Count a pause or resume."""
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
    assert harness.changes == 1

    await harness.planner.async_plan_all()
    resumed = harness.store.get(schedule.id)
    assert resumed is not None
    assert resumed.paused is None
    assert harness.planner.planned_run(schedule.id) is not None
    assert harness.changes == 2
    harness.planner.async_stop()

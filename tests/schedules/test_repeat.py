"""Tests for one-off and repeating schedules: commands, removal after the last run (concept 19.10)."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.haac_bridge.core.errors import ErrorCode, ScheduleError
from custom_components.haac_bridge.core.runtime import get_data
from custom_components.haac_bridge.schedules.model import (
    Repeat,
    RepeatFreq,
    RunEntry,
    RunResult,
    RunTrigger,
    Schedule,
)

from .conftest import ALL_DAYS, World, utc
from .test_api import CREATE, create, error_code, ws
from .test_runner import add, manager_of

CLIENT = Callable[[User], Coroutine[Any, Any, Any]]
MORNING = {"type": "time", "time": "07:45"}
WEEKLY_MORNING = {**MORNING, "days": ALL_DAYS}


@dataclass
class LogRecorder:
    """A run log that keeps what the bridge writes to it."""

    entries: list[RunEntry] = field(default_factory=list)

    def record(self, entry: RunEntry) -> None:
        """Keep the entry."""
        self.entries.append(entry)


def repeat_of(freq: str, start: date, *, interval: int = 1, end: date | None = None) -> Repeat:
    """Return the repeat rule of a test."""
    return Repeat(RepeatFreq(freq), 1 if freq == "once" else interval, start, end)


def iso(day: date) -> str:
    """Return a date as the commands carry it."""
    return day.isoformat()


@pytest.fixture
def log(hass: HomeAssistant, world: World) -> LogRecorder:
    """Replace the run log of the bridge by a recorder."""
    recorder = LogRecorder()
    get_data(hass).run_log = recorder
    return recorder


async def fire(hass: HomeAssistant, freezer: FrozenDateTimeFactory, moment: str) -> None:
    """Move the clock to `moment` and let the due timers and runs finish."""
    freezer.move_to(moment)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def plan(hass: HomeAssistant, schedule: Schedule) -> None:
    """Let the planner of the bridge plan a schedule that was added to the store."""
    await manager_of(hass).planner.async_plan(schedule.id)


# --- removal after the last run ------------------------------------------------------------------


@pytest.mark.usefixtures("berlin")
async def test_a_one_off_schedule_is_removed_after_its_run(
    hass: HomeAssistant, world: World, log: LogRecorder, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-19 05:00:00+00:00")
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(
        hass,
        world.anton.id,
        when=WEEKLY_MORNING,
        repeat=repeat_of("once", date(2026, 10, 19)),
        notify=True,
    )
    await plan(hass, schedule)
    assert manager_of(hass).store.get(schedule.id) is not None

    await fire(hass, freezer, "2026-10-19 05:45:01+00:00")
    assert len(calls) == 2
    assert manager_of(hass).store.get(schedule.id) is None
    assert manager_of(hass).planner.planned_run(schedule.id) is None
    [entry] = log.entries
    assert (entry.schedule_id, entry.owner, entry.name) == (
        schedule.id,
        world.anton.id,
        schedule.name,
    )
    assert (entry.result, entry.trigger, entry.removed, entry.notify) == (
        RunResult.OK,
        RunTrigger.PLAN,
        True,
        True,
    )


@pytest.mark.usefixtures("berlin")
async def test_a_one_off_schedule_is_removed_also_when_the_run_fails(
    hass: HomeAssistant, world: World, log: LogRecorder, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-19 05:00:00+00:00")
    async_mock_service(hass, "switch", "turn_on")
    schedule = await add(
        hass,
        world.anton.id,
        entities=["switch.ghost"],
        when=WEEKLY_MORNING,
        repeat=repeat_of("once", date(2026, 10, 19)),
    )
    await plan(hass, schedule)
    await fire(hass, freezer, "2026-10-19 05:45:01+00:00")
    assert manager_of(hass).store.get(schedule.id) is None
    [entry] = log.entries
    assert (entry.result, entry.code, entry.removed) == (RunResult.FAILED, "HAB-SCH-002", True)


@pytest.mark.usefixtures("berlin")
async def test_the_last_run_before_the_end_date_removes_the_schedule(
    hass: HomeAssistant, world: World, log: LogRecorder, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-19 05:00:00+00:00")
    async_mock_service(hass, "switch", "turn_on")
    schedule = await add(
        hass,
        world.anton.id,
        when=WEEKLY_MORNING,
        repeat=repeat_of("daily", date(2026, 10, 19), end=date(2026, 10, 20)),
    )
    await plan(hass, schedule)

    await fire(hass, freezer, "2026-10-19 05:45:01+00:00")
    assert manager_of(hass).store.get(schedule.id) is not None
    assert [entry.removed for entry in log.entries] == []  # the runner's own entries come with B3

    await fire(hass, freezer, "2026-10-20 05:45:01+00:00")
    assert manager_of(hass).store.get(schedule.id) is None
    assert [entry.removed for entry in log.entries] == [True]


@pytest.mark.usefixtures("berlin")
async def test_a_schedule_without_an_end_date_stays(
    hass: HomeAssistant, world: World, log: LogRecorder, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-10-19 05:00:00+00:00")
    async_mock_service(hass, "switch", "turn_on")
    schedule = await add(
        hass, world.anton.id, when=WEEKLY_MORNING, repeat=repeat_of("yearly", date(2026, 10, 19))
    )
    await plan(hass, schedule)
    await fire(hass, freezer, "2026-10-19 05:45:01+00:00")
    assert manager_of(hass).store.get(schedule.id) is not None
    assert manager_of(hass).planner.planned_run(schedule.id) == utc(2027, 10, 19, 5, 45)
    assert log.entries == []


async def test_run_now_removes_a_one_off_schedule_after_the_run(
    hass: HomeAssistant, world: World, log: LogRecorder
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    tomorrow = date.today() + timedelta(days=1)
    schedule = await add(
        hass, world.anton.id, when=WEEKLY_MORNING, repeat=repeat_of("once", tomorrow), enabled=False
    )
    await manager_of(hass).async_run_now(world.anton, schedule.id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(calls) == 2
    assert manager_of(hass).store.get(schedule.id) is None
    [entry] = log.entries
    assert (entry.trigger, entry.removed) == (RunTrigger.MANUAL, True)


@pytest.mark.parametrize("freq", ["daily", "weekly", "monthly", "yearly"])
async def test_run_now_keeps_a_repeating_schedule(
    hass: HomeAssistant, world: World, log: LogRecorder, freq: str
) -> None:
    async_mock_service(hass, "switch", "turn_on")
    today = date.today()
    schedule = await add(
        hass,
        world.anton.id,
        when=WEEKLY_MORNING,
        repeat=repeat_of(freq, today, end=today + timedelta(days=1)),
    )
    await manager_of(hass).async_run_now(world.anton, schedule.id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert manager_of(hass).store.get(schedule.id) is not None
    assert log.entries == []


async def test_a_missed_last_run_is_logged_and_removes_the_schedule(
    hass: HomeAssistant, world: World, log: LogRecorder
) -> None:
    schedule = await add(
        hass,
        world.anton.id,
        when=WEEKLY_MORNING,
        repeat=repeat_of("once", date(2026, 10, 19)),
        notify=True,
    )
    at = utc(2026, 10, 19, 5, 45)
    planner = manager_of(hass).planner
    assert planner.on_missed is not None
    await planner.on_missed(schedule, at, last=True)
    assert manager_of(hass).store.get(schedule.id) is None
    [entry] = log.entries
    assert (entry.at, entry.result, entry.trigger, entry.removed, entry.notify) == (
        at,
        RunResult.MISSED,
        RunTrigger.PLAN,
        True,
        True,
    )


async def test_a_missed_run_that_is_not_the_last_is_logged_and_the_schedule_stays(
    hass: HomeAssistant, world: World, log: LogRecorder
) -> None:
    schedule = await add(hass, world.anton.id, when=WEEKLY_MORNING)
    planner = manager_of(hass).planner
    assert planner.on_missed is not None
    await planner.on_missed(schedule, utc(2026, 10, 19, 5, 45), last=False)
    assert manager_of(hass).store.get(schedule.id) is not None
    [entry] = log.entries
    assert (entry.result, entry.removed) == (RunResult.MISSED, False)


# --- the commands --------------------------------------------------------------------------------


async def test_create_a_one_off_schedule(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    day = date.today() + timedelta(days=3)
    schedule = await create(anton, when=MORNING, repeat={"freq": "once", "start_date": iso(day)})
    assert schedule["repeat"] == {"freq": "once", "start_date": iso(day)}
    assert len(schedule["next_runs"]) == 1
    assert schedule["next_runs"][0] == schedule["next_run"]
    assert schedule["expired"] is False


async def test_create_a_repeating_schedule_with_an_end_date(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    start = date.today() + timedelta(days=1)
    schedule = await create(
        anton,
        when=MORNING,
        repeat={
            "freq": "daily",
            "interval": 2,
            "start_date": iso(start),
            "end_date": iso(start + timedelta(days=3)),
        },
    )
    assert schedule["repeat"]["interval"] == 2
    assert len(schedule["next_runs"]) == 2  # day 0 and day 2; the end date stops the third
    assert schedule["next_run"] == schedule["next_runs"][0]


async def test_a_schedule_without_repeat_is_weekly_and_lists_three_runs(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton)
    assert schedule["repeat"] == {"freq": "weekly", "interval": 1}
    assert len(schedule["next_runs"]) == 3
    listed = (await ws(anton, "schedules/list"))["result"]["schedules"]
    assert listed[0]["next_runs"] == schedule["next_runs"]
    assert listed[0]["expired"] is False


@pytest.mark.parametrize(
    "repeat",
    [
        {"freq": "hourly"},
        {"freq": "yearly", "interval": 2},
        {"freq": "daily", "interval": 366},
        {"freq": "weekly", "interval": 0},
        {"freq": "once"},
        {"freq": "once", "start_date": "2099-01-01"},
        {"freq": "daily", "start_date": "2026-13-01"},
        {"freq": "daily", "start_date": "2026-10-05", "end_date": "2026-10-04"},
        {"freq": "daily", "unknown": 1},
        "daily",
    ],
)
async def test_an_invalid_repeat_is_refused(world: World, client_for: CLIENT, repeat: Any) -> None:
    anton = await client_for(world.anton)
    reply = await ws(anton, "schedules/create", **{**CREATE, "when": MORNING, "repeat": repeat})
    assert error_code(reply) == "HAB-SCH-001"


async def test_once_with_an_end_date_is_refused(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    start = iso(date.today() + timedelta(days=2))
    repeat = {"freq": "once", "start_date": start, "end_date": start}
    reply = await ws(anton, "schedules/create", **{**CREATE, "when": MORNING, "repeat": repeat})
    assert error_code(reply) == "HAB-SCH-001"


async def test_a_date_in_the_past_is_refused(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    yesterday = iso(date.today() - timedelta(days=2))
    for repeat in (
        {"freq": "once", "start_date": yesterday},
        {"freq": "daily", "start_date": yesterday, "end_date": yesterday},
    ):
        reply = await ws(anton, "schedules/create", **{**CREATE, "when": MORNING, "repeat": repeat})
        assert error_code(reply) == "HAB-SCH-009"


async def test_weekdays_are_required_for_weekly_only(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    reply = await ws(
        anton,
        "schedules/create",
        **{**CREATE, "when": MORNING, "repeat": {"freq": "weekly", "interval": 2}},
    )
    assert error_code(reply) == "HAB-SCH-001"
    daily = await create(anton, when=MORNING, repeat={"freq": "daily"})
    assert "days" not in daily["when"]
    start = iso(date.today() + timedelta(days=1))
    monthly = await create(
        anton, when={**MORNING, "days": [0]}, repeat={"freq": "monthly", "start_date": start}
    )
    assert monthly["repeat"]["freq"] == "monthly"


async def test_update_the_date_rule(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton)
    start = iso(date.today() + timedelta(days=4))
    reply = await ws(
        anton,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        repeat={"freq": "once", "start_date": start},
    )
    assert reply["success"], reply
    assert reply["result"]["repeat"] == {"freq": "once", "start_date": start}
    assert len(reply["result"]["next_runs"]) == 1


async def test_update_to_weekly_needs_weekdays(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton, when=MORNING, repeat={"freq": "daily"})
    reply = await ws(
        anton,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        repeat={"freq": "weekly", "interval": 1},
    )
    assert error_code(reply) == "HAB-SCH-001"


async def test_an_expired_schedule_needs_a_new_date_to_be_enabled(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    gone = date.today() - timedelta(days=3)
    expired = await add(
        hass, world.anton.id, when=WEEKLY_MORNING, repeat=repeat_of("once", gone), enabled=False
    )
    listed = (await ws(anton, "schedules/list"))["result"]["schedules"]
    assert [(item["expired"], item["next_run"], item["next_runs"]) for item in listed] == [
        (True, None, [])
    ]

    reply = await ws(
        anton,
        "schedules/update",
        schedule_id=expired.id,
        updated_at=expired.updated_at.isoformat(),
        enabled=True,
    )
    assert error_code(reply) == "HAB-SCH-009"
    with pytest.raises(ScheduleError) as raised:
        await manager_of(hass).async_set_enabled(expired.id, enabled=True)
    assert raised.value.code is ErrorCode.SCH_IN_PAST

    new_day = iso(date.today() + timedelta(days=5))
    reply = await ws(
        anton,
        "schedules/update",
        schedule_id=expired.id,
        updated_at=expired.updated_at.isoformat(),
        enabled=True,
        repeat={"freq": "once", "start_date": new_day},
    )
    assert reply["success"], reply
    assert reply["result"]["expired"] is False
    assert reply["result"]["enabled"] is True


async def test_renaming_an_expired_schedule_is_allowed(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    gone = date.today() - timedelta(days=3)
    expired = await add(
        hass, world.anton.id, when=WEEKLY_MORNING, repeat=repeat_of("once", gone), enabled=False
    )
    reply = await ws(
        anton,
        "schedules/update",
        schedule_id=expired.id,
        updated_at=expired.updated_at.isoformat(),
        name="Heater",
    )
    assert reply["success"], reply
    assert reply["result"]["expired"] is True


async def test_preview_returns_the_next_runs_without_saving(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    start = date.today() + timedelta(days=10)
    reply = await ws(
        anton,
        "schedules/preview",
        when=MORNING,
        repeat={"freq": "monthly", "interval": 2, "start_date": iso(start)},
    )
    assert reply["success"], reply
    runs = reply["result"]["next_runs"]
    assert len(runs) == 3
    assert runs == sorted(runs)
    assert (await ws(anton, "schedules/list"))["result"]["schedules"] == []


async def test_preview_without_repeat_is_weekly(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    reply = await ws(
        anton,
        "schedules/preview",
        when={"type": "time", "time": "06:00", "days": [0, 1, 2, 3, 4, 5, 6]},
    )
    assert len(reply["result"]["next_runs"]) == 3
    assert error_code(await ws(anton, "schedules/preview", when=MORNING)) == "HAB-SCH-001"


async def test_preview_validates_like_create(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    past = {"freq": "once", "start_date": iso(date.today() - timedelta(days=2))}
    assert (
        error_code(await ws(anton, "schedules/preview", when=MORNING, repeat=past)) == "HAB-SCH-009"
    )
    bad = {"freq": "yearly", "interval": 3}
    assert (
        error_code(await ws(anton, "schedules/preview", when=MORNING, repeat=bad)) == "HAB-SCH-001"
    )
    assert error_code(await ws(anton, "schedules/preview")) == "HAB-WS-001"


async def test_preview_of_a_finished_range_is_empty(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    start = date.today() + timedelta(days=1)
    repeat = {"freq": "daily", "start_date": iso(start), "end_date": iso(start)}
    reply = await ws(anton, "schedules/preview", when=MORNING, repeat=repeat)
    assert len(reply["result"]["next_runs"]) == 1


async def test_info_reports_the_repeat_feature(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    assert "schedule_repeat" in (await ws(anton, "info"))["result"]["features"]

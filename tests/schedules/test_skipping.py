"""Tests for skipped runs: the date rule, the command and the effect on the plan (concept 19.12)."""

from collections.abc import Callable, Coroutine
from datetime import date
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
from custom_components.haac_bridge.schedules.model import (
    RepeatFreq,
    parse_repeat,
    parse_skipped_dates,
    schedule_from_dict,
)
from custom_components.haac_bridge.schedules.recurrence import RecurrenceFactory
from custom_components.haac_bridge.schedules.skipping import SkippingRule

from .conftest import World, make_schedule
from .test_api import create, error_code, ws
from .test_runner import manager_of

CLIENT = Callable[[User], Coroutine[Any, Any, Any]]
WORKDAYS = [0, 1, 2, 3, 4]
EVERY_SECOND_WEEK = {"freq": "weekly", "interval": 2, "start_date": "2026-11-02"}
NOW = "2026-11-02 05:00:00+00:00"
"""A Monday, before the 07:45 run (06:45 UTC in Berlin in winter)."""


def rule_of(*skipped: str) -> SkippingRule:
    """Return the workdays of every second week without the skipped dates."""
    inner = RecurrenceFactory().create(parse_repeat(EVERY_SECOND_WEEK), frozenset(WORKDAYS))
    return SkippingRule(inner, frozenset(date.fromisoformat(day) for day in skipped))


def test_a_skipped_date_is_no_run_date() -> None:
    rule = rule_of("2026-11-04")
    assert rule.matches(date(2026, 11, 3))
    assert not rule.matches(date(2026, 11, 4))
    assert rule.next_date(date(2026, 11, 3)) == date(2026, 11, 5)
    assert rule.previous_date(date(2026, 11, 4)) == date(2026, 11, 3)


def test_a_whole_skipped_week_is_jumped_over() -> None:
    week = [f"2026-11-0{day}" for day in range(2, 7)]
    rule = rule_of(*week)
    assert rule.next_date(date(2026, 11, 1)) == date(2026, 11, 16)
    assert rule.previous_date(date(2026, 11, 15)) is None


def test_the_rule_is_unchanged_without_skips() -> None:
    assert RepeatFreq.WEEKLY.value == "weekly"
    assert rule_of().next_date(date(2026, 11, 6)) == date(2026, 11, 16)


async def make(client: Any, **changes: Any) -> dict[str, Any]:
    """Create a workday schedule that runs every second week at 07:45 and return it."""
    fields = {
        "when": {"type": "time", "time": "07:45", "days": WORKDAYS},
        "repeat": EVERY_SECOND_WEEK,
        **changes,
    }
    return await create(client, **fields)


@pytest.mark.usefixtures("berlin")
async def test_skipping_a_run_marks_it_and_moves_the_plan(
    world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await make(anton)
    assert [run["skipped"] for run in schedule["upcoming_runs"]] == [False] * 3
    assert [run["date"] for run in schedule["upcoming_runs"]] == [
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
    ]
    assert schedule["upcoming_runs"][0]["at"] == "2026-11-02T06:45:00+00:00"

    reply = await ws(
        anton, "schedules/skip_run", schedule_id=schedule["id"], date="2026-11-02", skip=True
    )
    assert reply["success"], reply
    result = reply["result"]
    assert result["skipped_dates"] == ["2026-11-02"]
    assert result["updated_at"] == schedule["updated_at"]
    assert result["next_run"] == "2026-11-03T06:45:00+00:00"
    assert [run["skipped"] for run in result["upcoming_runs"]] == [True, False, False, False]
    assert result["next_runs"] == [
        "2026-11-03T06:45:00+00:00",
        "2026-11-04T06:45:00+00:00",
        "2026-11-05T06:45:00+00:00",
    ]


@pytest.mark.usefixtures("berlin")
async def test_a_skipped_run_does_not_fire_but_the_next_one_does(
    hass: HomeAssistant, world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    calls = async_mock_service(hass, "switch", "turn_on")
    anton = await client_for(world.anton)
    schedule = await make(anton)
    await ws(anton, "schedules/skip_run", schedule_id=schedule["id"], date="2026-11-02", skip=True)

    freezer.move_to("2026-11-02 06:50:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert not calls

    freezer.move_to("2026-11-03 06:50:00+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(calls) == 1


@pytest.mark.usefixtures("berlin")
async def test_taking_a_run_up_again_removes_the_mark(
    world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await make(anton)
    command = {"schedule_id": schedule["id"], "date": "2026-11-03"}
    await ws(anton, "schedules/skip_run", skip=True, **command)
    reply = await ws(anton, "schedules/skip_run", skip=False, **command)
    assert reply["result"]["skipped_dates"] == []
    assert reply["result"]["next_run"] == "2026-11-02T06:45:00+00:00"


@pytest.mark.usefixtures("berlin")
async def test_the_revision_follows_a_skip(
    world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await make(anton)
    before = (await ws(anton, "schedules/revision"))["result"]["revision"]
    await ws(anton, "schedules/skip_run", schedule_id=schedule["id"], date="2026-11-04", skip=True)
    after = (await ws(anton, "schedules/revision"))["result"]["revision"]
    assert before != after


@pytest.mark.usefixtures("berlin")
@pytest.mark.parametrize(
    "day",
    ["2026-11-09", "2026-11-07", "2026-10-30", "2027-05-03"],
    ids=["off-week", "weekend", "past", "too-far-ahead"],
)
async def test_only_one_of_the_next_runs_can_be_skipped(
    world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory, day: str
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await make(anton)
    reply = await ws(anton, "schedules/skip_run", schedule_id=schedule["id"], date=day, skip=True)
    assert error_code(reply) == "HAB-SCH-010"


@pytest.mark.usefixtures("berlin")
async def test_a_bad_date_is_invalid(
    world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await make(anton)
    reply = await ws(
        anton, "schedules/skip_run", schedule_id=schedule["id"], date="soon", skip=True
    )
    assert error_code(reply) == "HAB-SCH-001"


@pytest.mark.usefixtures("berlin")
async def test_a_one_off_schedule_cannot_be_skipped(
    world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await create(
        anton,
        when={"type": "time", "time": "07:45"},
        repeat={"freq": "once", "start_date": "2026-11-04"},
    )
    reply = await ws(
        anton, "schedules/skip_run", schedule_id=schedule["id"], date="2026-11-04", skip=True
    )
    assert error_code(reply) == "HAB-SCH-010"


@pytest.mark.usefixtures("berlin")
async def test_the_last_run_cannot_be_skipped(
    world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await make(anton, repeat={**EVERY_SECOND_WEEK, "end_date": "2026-11-03"})
    first = await ws(
        anton, "schedules/skip_run", schedule_id=schedule["id"], date="2026-11-02", skip=True
    )
    assert first["success"], first
    last = await ws(
        anton, "schedules/skip_run", schedule_id=schedule["id"], date="2026-11-03", skip=True
    )
    assert error_code(last) == "HAB-SCH-010"


@pytest.mark.usefixtures("berlin")
async def test_only_the_owner_and_admins_may_skip(
    world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await make(anton)
    command = {"schedule_id": schedule["id"], "date": "2026-11-02", "skip": True}
    assert (
        error_code(await ws(await client_for(world.lena), "schedules/skip_run", **command))
        == "HAB-SCH-006"
    )
    assert (await ws(await client_for(world.root), "schedules/skip_run", **command))["success"]


@pytest.mark.usefixtures("berlin")
async def test_changing_the_weekdays_drops_skips_that_are_no_runs_any_more(
    hass: HomeAssistant, world: World, client_for: CLIENT, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to(NOW)
    anton = await client_for(world.anton)
    schedule = await make(anton)
    for day in ("2026-11-03", "2026-11-06"):
        await ws(anton, "schedules/skip_run", schedule_id=schedule["id"], date=day, skip=True)
    reply = await ws(
        anton,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        when={"type": "time", "time": "07:45", "days": [0, 1, 2, 3]},
    )
    assert reply["success"], reply
    assert reply["result"]["skipped_dates"] == ["2026-11-03"]
    stored = manager_of(hass).store.get(schedule["id"])
    assert stored is not None
    assert stored.skipped_dates == {date(2026, 11, 3)}


def test_skipped_dates_survive_the_stored_form() -> None:
    schedule = make_schedule(skipped_dates=frozenset({date(2026, 11, 4), date(2026, 11, 3)}))
    stored = schedule.to_dict()
    assert stored["skipped_dates"] == ["2026-11-03", "2026-11-04"]
    assert schedule_from_dict(stored).skipped_dates == schedule.skipped_dates
    assert schedule_from_dict({**stored, "skipped_dates": None}).skipped_dates == frozenset()
    del stored["skipped_dates"]
    assert schedule_from_dict(stored).skipped_dates == frozenset()


@pytest.mark.parametrize("raw", ["2026-11-04", [4], ["not a date"], ["2026-11-04"] * 31])
def test_damaged_skipped_dates_are_invalid(raw: object) -> None:
    with pytest.raises(ScheduleError) as error:
        parse_skipped_dates(raw)
    assert error.value.code is ErrorCode.SCH_INVALID

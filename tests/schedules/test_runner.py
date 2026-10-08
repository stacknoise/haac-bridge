"""Tests for running a schedule: owner and exposure re-checks, retry, results (concept 19.3)."""

import asyncio
from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import Unauthorized
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.haac_bridge.core.runtime import get_data
from custom_components.haac_bridge.schedules.manager import ScheduleManager
from custom_components.haac_bridge.schedules.model import PauseReason, RunResult, Schedule

from .conftest import World, make_schedule

BOTH = ["switch.garage_socket", "switch.office_fan"]


def manager_of(hass: HomeAssistant) -> ScheduleManager:
    """Return the schedule manager of the bridge."""
    return get_data(hass).schedules


async def add(hass: HomeAssistant, owner: str, **fields: Any) -> Schedule:
    """Store a schedule for `owner` directly, without the exposure check of the command."""
    entities = fields.pop("entities", BOTH)
    schedule = make_schedule(owner=owner, entities=tuple(entities), **fields)
    await manager_of(hass).store.async_add(schedule)
    return schedule


def entities_of(calls: list[ServiceCall]) -> list[str]:
    """Return the entity of every recorded service call."""
    result: list[str] = []
    for call in calls:
        target = call.data["entity_id"]
        result.extend([target] if isinstance(target, str) else target)
    return result


async def test_switches_every_entity_as_the_owner(hass: HomeAssistant, world: World) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.anton.id)
    await manager_of(hass).runner.async_run(schedule.id)

    assert entities_of(calls) == BOTH
    assert {call.context.user_id for call in calls} == {world.anton.id}
    stored = manager_of(hass).store.get(schedule.id)
    assert stored is not None
    assert stored.last_run is not None
    assert stored.last_run.result is RunResult.OK
    assert stored.last_run.code is None
    assert stored.paused is None


@pytest.mark.parametrize("action", ["turn_on", "turn_off", "toggle"])
async def test_the_action_selects_the_service(
    hass: HomeAssistant, world: World, action: str
) -> None:
    calls = {
        name: async_mock_service(hass, "switch", name) for name in ("turn_on", "turn_off", "toggle")
    }
    schedule = await add(hass, world.anton.id)
    schedule = schedule.with_changes(action=type(schedule.action)(action))
    await manager_of(hass).store.async_replace(schedule)
    await manager_of(hass).runner.async_run(schedule.id)

    for name, recorded in calls.items():
        assert len(recorded) == (2 if name == action else 0), name


async def test_an_entity_that_is_not_exposed_is_skipped(hass: HomeAssistant, world: World) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.lena.id)  # lena sees only the fan
    await manager_of(hass).runner.async_run(schedule.id)

    assert entities_of(calls) == ["switch.office_fan"]
    stored = manager_of(hass).store.get(schedule.id)
    assert stored is not None
    assert stored.last_run is not None
    assert stored.last_run.result is RunResult.PARTIAL
    assert stored.last_run.code == "HAB-SCH-002"
    assert stored.paused is None


async def test_a_schedule_without_exposed_entities_is_paused(
    hass: HomeAssistant, world: World
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.lena.id, entities=["switch.garage_socket"])
    await manager_of(hass).runner.async_run(schedule.id)

    assert calls == []
    stored = manager_of(hass).store.get(schedule.id)
    assert stored is not None
    assert stored.paused is not None
    assert stored.paused.reason is PauseReason.NO_ENTITIES
    assert stored.last_run is not None
    assert stored.last_run.result is RunResult.FAILED
    assert manager_of(hass).planner.planned_run(schedule.id) is None


async def test_an_entity_without_a_state_counts_as_failed(
    hass: HomeAssistant, world: World
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.anton.id, entities=["switch.garage_socket", "switch.ghost"])
    await manager_of(hass).runner.async_run(schedule.id)

    assert entities_of(calls) == ["switch.garage_socket"]
    stored = manager_of(hass).store.get(schedule.id)
    assert stored is not None
    assert stored.last_run is not None
    assert stored.last_run.result is RunResult.PARTIAL


async def test_an_unavailable_entity_is_tried_again_and_then_works(
    hass: HomeAssistant, world: World
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    hass.states.async_set("switch.office_fan", "unavailable")
    schedule = await add(hass, world.anton.id)
    manager = manager_of(hass)

    async def _back_online() -> None:
        assert entities_of(calls) == ["switch.garage_socket"]
        hass.states.async_set("switch.office_fan", "off")

    with patch.object(manager.runner, "_async_wait_before_retry", _back_online):
        await manager.runner.async_run(schedule.id)

    assert entities_of(calls) == BOTH
    stored = manager.store.get(schedule.id)
    assert stored is not None
    assert stored.last_run is not None
    assert stored.last_run.result is RunResult.OK


async def test_an_entity_that_stays_unavailable_fails(hass: HomeAssistant, world: World) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    hass.states.async_set("switch.office_fan", "unavailable")
    schedule = await add(hass, world.anton.id)
    manager = manager_of(hass)

    async def _no_wait() -> None:
        return None

    with patch.object(manager.runner, "_async_wait_before_retry", _no_wait):
        await manager.runner.async_run(schedule.id)

    assert entities_of(calls) == ["switch.garage_socket"]
    stored = manager.store.get(schedule.id)
    assert stored is not None
    assert stored.last_run is not None
    assert stored.last_run.result is RunResult.PARTIAL
    assert stored.last_run.code == "HAB-SCH-002"


async def test_every_entity_failing_gives_failed(hass: HomeAssistant, world: World) -> None:
    async def _refuse(call: ServiceCall) -> None:
        raise Unauthorized(context=call.context)

    hass.services.async_register("switch", "turn_on", _refuse)
    schedule = await add(hass, world.anton.id)
    await manager_of(hass).runner.async_run(schedule.id)

    stored = manager_of(hass).store.get(schedule.id)
    assert stored is not None
    assert stored.last_run is not None
    assert stored.last_run.result is RunResult.FAILED
    assert stored.last_run.code == "HAB-SCH-002"


async def test_an_inactive_owner_pauses_the_schedule(hass: HomeAssistant, world: World) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.anton.id)
    world.anton.is_active = False
    await manager_of(hass).runner.async_run(schedule.id)

    assert calls == []
    stored = manager_of(hass).store.get(schedule.id)
    assert stored is not None
    assert stored.paused is not None
    assert stored.paused.reason is PauseReason.OWNER_INACTIVE
    assert manager_of(hass).planner.planned_run(schedule.id) is None


async def test_a_deleted_owner_loses_the_schedule(hass: HomeAssistant, world: World) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.anton.id)
    await hass.auth.async_remove_user(world.anton)
    await manager_of(hass).runner.async_run(schedule.id)

    assert calls == []
    assert manager_of(hass).store.get(schedule.id) is None


async def test_an_owner_who_is_not_configured_loses_the_schedule(
    hass: HomeAssistant, world: World
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.bob.id)
    await manager_of(hass).runner.async_run(schedule.id)

    assert calls == []
    assert manager_of(hass).store.get(schedule.id) is None


async def test_running_an_unknown_schedule_does_nothing(hass: HomeAssistant, world: World) -> None:
    await manager_of(hass).runner.async_run("unknown")


async def test_a_run_tells_subscribers(hass: HomeAssistant, world: World) -> None:
    async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.anton.id)
    before = manager_of(hass).revision_for(world.anton)
    await manager_of(hass).runner.async_run(schedule.id)
    assert manager_of(hass).revision_for(world.anton) != before


async def test_a_hanging_service_fails_the_run_and_frees_the_schedule(
    hass: HomeAssistant, world: World
) -> None:
    async def _hang(call: ServiceCall) -> None:
        await asyncio.sleep(3600)

    hass.services.async_register("switch", "turn_on", _hang)
    schedule = await add(hass, world.anton.id)
    runner = manager_of(hass).runner
    with patch("custom_components.haac_bridge.services.call_factory.SERVICE_TIMEOUT", 0.05):
        await asyncio.wait_for(runner.async_run(schedule.id), timeout=5)
        stored = manager_of(hass).store.get(schedule.id)
        assert stored is not None
        assert stored.last_run is not None
        assert stored.last_run.result is RunResult.FAILED
        # The lock is free again: a second run finishes as well.
        await asyncio.wait_for(runner.async_run(schedule.id), timeout=5)

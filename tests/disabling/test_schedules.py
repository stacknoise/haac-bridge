"""Tests for the effect of a deactivated entity on schedules: switch off, block, switch on again (concept 7.5)."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.haac_bridge.const import DOMAIN
from custom_components.haac_bridge.core.runtime import get_data
from custom_components.haac_bridge.schedules.entities import SUFFIX_ENABLED, unique_id
from custom_components.haac_bridge.schedules.model import RunResult

from ..schedules.conftest import World
from ..schedules.test_runner import add
from .helpers import CLIENT, FAN, GARAGE, create, error_code, set_disabled, ws

BOTH = [GARAGE, FAN]


async def schedule_of(client: Any, schedule_id: str) -> dict[str, Any]:
    """Return one schedule from schedules/list."""
    listing = (await ws(client, "schedules/list"))["result"]["schedules"]
    return next(item for item in listing if item["id"] == schedule_id)


async def test_deactivating_switches_the_schedules_off_and_blocks_them(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    single = await create(anton)
    several = await create(anton, name="Both", entities=BOTH)
    unrelated = await create(anton, name="Fan", entities=[FAN])

    result = await set_disabled(anton, GARAGE)
    assert sorted(result["schedules_changed"]) == sorted([single["id"], several["id"]])

    for schedule_id, blocked in ((single["id"], [GARAGE]), (several["id"], [GARAGE])):
        schedule = await schedule_of(anton, schedule_id)
        assert schedule["enabled"] is False
        assert schedule["off_reason"] == "entity_disabled"
        assert schedule["blocked_by"] == blocked
        assert schedule["next_run"] is None
    fan = await schedule_of(anton, unrelated["id"])
    assert fan["enabled"] is True
    assert fan["blocked_by"] == []
    assert fan["off_reason"] is None


async def test_a_blocked_schedule_cannot_be_enabled_or_run(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    root = await client_for(world.root)
    schedule = await create(anton)
    await set_disabled(anton, GARAGE)
    blocked = await schedule_of(anton, schedule["id"])

    for client in (anton, root):
        reply = await ws(
            client,
            "schedules/update",
            schedule_id=schedule["id"],
            updated_at=blocked["updated_at"],
            enabled=True,
        )
        assert error_code(reply) == "HAB-SCH-008"
        assert error_code(await ws(client, "schedules/run_now", schedule_id=schedule["id"])) == (
            "HAB-SCH-008"
        )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert (await schedule_of(anton, schedule["id"]))["last_run"] is None

    switch = er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, unique_id(schedule["id"], SUFFIX_ENABLED)
    )
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=True)
    assert (await schedule_of(anton, schedule["id"]))["enabled"] is False


async def test_a_blocked_schedule_can_still_be_renamed_and_kept_off(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton)
    await set_disabled(anton, GARAGE)
    blocked = await schedule_of(anton, schedule["id"])

    reply = await ws(
        anton,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=blocked["updated_at"],
        name="Renamed",
        enabled=False,
    )
    assert reply["success"], reply
    assert reply["result"]["off_reason"] == "entity_disabled"
    assert reply["result"]["blocked_by"] == [GARAGE]


async def test_activating_switches_the_schedules_on_again(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    off_by_hand = await create(anton, name="By hand", enabled=False)
    schedule = await create(anton)
    several = await create(anton, name="Both", entities=BOTH)
    await set_disabled(anton, GARAGE)
    await set_disabled(anton, FAN)

    result = await set_disabled(anton, GARAGE, disabled=False)
    assert result["schedules_changed"] == [schedule["id"]]
    again = await schedule_of(anton, schedule["id"])
    assert again["enabled"] is True
    assert again["off_reason"] is None
    assert again["blocked_by"] == []
    assert again["next_run"] is not None
    still = await schedule_of(anton, several["id"])
    assert still["enabled"] is False
    assert still["blocked_by"] == [FAN]

    result = await set_disabled(anton, FAN, disabled=False)
    assert result["schedules_changed"] == [several["id"]]
    assert (await schedule_of(anton, several["id"]))["enabled"] is True
    # The schedule the user switched off themselves was not touched.
    assert (await schedule_of(anton, off_by_hand["id"]))["enabled"] is False


async def test_a_schedule_switched_off_by_hand_is_only_blocked(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton, enabled=False)
    assert (await set_disabled(anton, GARAGE))["schedules_changed"] == []
    off = await schedule_of(anton, schedule["id"])
    assert off["off_reason"] is None
    assert off["blocked_by"] == [GARAGE]

    assert (await set_disabled(anton, GARAGE, disabled=False))["schedules_changed"] == []
    assert (await schedule_of(anton, schedule["id"]))["enabled"] is False


async def test_the_revision_changes_when_a_schedule_becomes_blocked(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    await create(anton, enabled=False)
    before = (await ws(anton, "schedules/revision"))["result"]["revision"]
    await set_disabled(anton, GARAGE)
    blocked = (await ws(anton, "schedules/revision"))["result"]["revision"]
    await set_disabled(anton, GARAGE, disabled=False)
    after = (await ws(anton, "schedules/revision"))["result"]["revision"]
    assert len({before, blocked, after}) == 3


async def test_the_schedules_of_other_users_are_not_touched(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    root = await client_for(world.root)
    mine = await create(anton)
    theirs = await create(root)

    assert (await set_disabled(anton, GARAGE))["schedules_changed"] == [mine["id"]]
    assert (await schedule_of(root, theirs["id"]))["enabled"] is True
    # An admin sees the block on a foreign schedule but cannot lift it.
    assert (await schedule_of(root, mine["id"]))["blocked_by"] == [GARAGE]
    assert (await set_disabled(root, GARAGE))["disabled"] == [GARAGE]
    assert (await set_disabled(root, GARAGE, disabled=False))["schedules_changed"] == [theirs["id"]]
    assert (await schedule_of(root, mine["id"]))["enabled"] is False


async def test_creating_a_schedule_with_a_deactivated_entity(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    await set_disabled(anton, GARAGE)
    fields = {
        "name": "New",
        "when": {"type": "time", "time": "06:45", "days": [0]},
        "action": "turn_on",
        "entities": [GARAGE],
    }
    assert error_code(await ws(anton, "schedules/create", **fields)) == "HAB-SCH-008"
    off = await ws(anton, "schedules/create", **fields, enabled=False)
    assert off["success"], off
    assert off["result"]["blocked_by"] == [GARAGE]


async def test_the_runner_never_switches_a_deactivated_entity(
    hass: HomeAssistant, world: World
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await add(hass, world.anton.id, entities=BOTH)
    await get_data(hass).disabled.async_set(world.anton.id, GARAGE, True)

    await get_data(hass).schedules.runner.async_run(schedule.id)
    assert [call.data["entity_id"] for call in calls] == [FAN]
    stored = get_data(hass).schedules.store.get(schedule.id)
    assert stored is not None
    assert stored.last_run is not None
    assert stored.last_run.result is RunResult.PARTIAL

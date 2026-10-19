"""Tests for entities/set_disabled, `disabled` in entities/list, the event and the lock in call_service (concept 7.5)."""

from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.haac_bridge.core.runtime import get_data

from ..schedules.conftest import World
from .helpers import CLIENT, FAN, GARAGE, error_code, set_disabled, ws


async def listed(client: Any) -> dict[str, bool]:
    """Return `disabled` of every entity in entities/list."""
    reply = await ws(client, "entities/list")
    assert reply["success"], reply
    return {item["entity_id"]: item["disabled"] for item in reply["result"]["entities"]}


async def test_set_disabled_replies_with_the_full_list(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    assert await set_disabled(anton, GARAGE) == {"disabled": [GARAGE], "schedules_changed": []}
    assert await set_disabled(anton, FAN) == {"disabled": [GARAGE, FAN], "schedules_changed": []}
    assert await set_disabled(anton, GARAGE, disabled=False) == {
        "disabled": [FAN],
        "schedules_changed": [],
    }


async def test_repeating_a_change_changes_nothing(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    await set_disabled(anton, GARAGE)
    assert await set_disabled(anton, GARAGE) == {"disabled": [GARAGE], "schedules_changed": []}
    assert await set_disabled(anton, FAN, disabled=False) == {
        "disabled": [GARAGE],
        "schedules_changed": [],
    }


async def test_the_list_marks_deactivated_entities_per_user(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    root = await client_for(world.root)
    await set_disabled(anton, GARAGE)

    assert await listed(anton) == {GARAGE: True, FAN: False}
    assert await listed(root) == {GARAGE: False, FAN: False}


async def test_an_entity_that_is_not_exposed_is_refused(world: World, client_for: CLIENT) -> None:
    lena = await client_for(world.lena)
    for entity_id in (GARAGE, "light.kitchen", "switch.nope"):
        reply = await ws(lena, "entities/set_disabled", entity_id=entity_id, disabled=True)
        assert error_code(reply) == "HAB-ENT-001"
    assert (await ws(lena, "entities/set_disabled", entity_id=FAN, disabled=True))["success"]


async def test_an_entry_of_an_entity_that_is_gone_can_be_lifted(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    lena = await client_for(world.lena)
    await get_data(hass).disabled.async_set(world.lena.id, GARAGE, True)

    assert await set_disabled(lena, GARAGE, disabled=False) == {
        "disabled": [],
        "schedules_changed": [],
    }


async def test_the_limit_per_user_is_enforced(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    with patch("custom_components.haac_bridge.disabling.manager.MAX_DISABLED_PER_USER", 1):
        await set_disabled(anton, GARAGE)
        assert (
            error_code(await ws(anton, "entities/set_disabled", entity_id=FAN, disabled=True))
            == "HAB-WS-001"
        )
        assert await set_disabled(anton, GARAGE) == {
            "disabled": [GARAGE],
            "schedules_changed": [],
        }


async def test_the_request_is_validated(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    reply = await ws(anton, "entities/set_disabled", entity_id=GARAGE, disabled="yes")
    assert error_code(reply) == "HAB-WS-001"


async def test_every_connection_of_the_user_gets_the_event(
    world: World, client_for: CLIENT
) -> None:
    anton_phone = await client_for(world.anton)
    anton_tablet = await client_for(world.anton)
    anton_commands = await client_for(world.anton)
    root = await client_for(world.root)
    root_commands = await client_for(world.root)
    for client in (anton_phone, anton_tablet, root):
        await client.send_json_auto_id({"type": "haac_bridge/subscribe_entities"})
        assert (await client.receive_json())["success"]
        await client.receive_json()

    await set_disabled(anton_commands, GARAGE)
    for client in (anton_phone, anton_tablet):
        event = await client.receive_json()
        assert event["event"] == {"disabled_changed": {"disabled": [GARAGE]}}

    await set_disabled(root_commands, FAN)
    assert (await root.receive_json())["event"] == {"disabled_changed": {"disabled": [FAN]}}
    await set_disabled(anton_commands, GARAGE, disabled=False)
    assert (await anton_tablet.receive_json())["event"] == {"disabled_changed": {"disabled": []}}


async def test_call_service_refuses_a_deactivated_entity(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    anton = await client_for(world.anton)
    root = await client_for(world.root)
    call = {"entity_id": GARAGE, "service": "turn_on", "service_data": {}}
    await set_disabled(anton, GARAGE)

    assert error_code(await ws(anton, "call_service", **call)) == "HAB-ENT-002"
    assert calls == []
    assert (await ws(root, "call_service", **call))["success"]
    assert len(calls) == 1

    await set_disabled(anton, GARAGE, disabled=False)
    assert (await ws(anton, "call_service", **call))["success"]
    assert len(calls) == 2


async def test_an_unexposed_entity_stays_not_allowed_even_if_deactivated(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    lena = await client_for(world.lena)
    await get_data(hass).disabled.async_set(world.lena.id, GARAGE, True)
    call = {"entity_id": GARAGE, "service": "turn_on", "service_data": {}}
    assert error_code(await ws(lena, "call_service", **call)) == "HAB-SVC-001"

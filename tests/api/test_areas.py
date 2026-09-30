"""Tests for haac_bridge/areas (concept 6.3, 11.2)."""

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

SetupBridge = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

CONFIG = {
    "users": [
        {
            "username": "anton",
            "filter": {
                "include_entities": ["switch.garage_socket", "sensor.living_room_temperature"]
            },
        }
    ],
}


@pytest.fixture
async def anton_client(
    hass: HomeAssistant,
    hass_ws_client: Callable[..., Coroutine[Any, Any, Any]],
    add_user: Callable[[str], User],
    access_token_for: Callable[[User], Coroutine[Any, Any, str]],
    setup_bridge: SetupBridge,
) -> Any:
    """Return a WebSocket client signed in as the configured user anton."""
    anton = add_user("anton")
    await setup_bridge(CONFIG)
    return await hass_ws_client(hass, await access_token_for(anton))


async def _areas(client: Any) -> dict[str, Any]:
    """Send haac_bridge/areas and return its reply."""
    await client.send_json_auto_id({"type": "haac_bridge/areas"})
    return await client.receive_json()


@pytest.mark.usefixtures("demo_states")
async def test_areas_hold_only_exposed_entities(hass: HomeAssistant, anton_client: Any) -> None:
    ground = fr.async_get(hass).async_create("Ground floor", level=0)
    unused = fr.async_get(hass).async_create("Attic", level=2)
    garage = ar.async_get(hass).async_create("Garage", floor_id=ground.floor_id)
    living = ar.async_get(hass).async_create("Living room")
    hidden = ar.async_get(hass).async_create("Server room")
    ar.async_get(hass).async_create("Empty attic room", floor_id=unused.floor_id)

    entities = er.async_get(hass)
    socket = entities.async_get_or_create(
        "switch", "test", "1", suggested_object_id="garage_socket"
    )
    assert socket.entity_id == "switch.garage_socket"
    entities.async_update_entity(socket.entity_id, area_id=garage.id)

    # The temperature sensor takes the area of its device.
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "d1")}
    )
    dr.async_get(hass).async_update_device(device.id, area_id=living.id)
    sensor = entities.async_get_or_create(
        "sensor", "test", "2", suggested_object_id="living_room_temperature", device_id=device.id
    )
    assert sensor.entity_id == "sensor.living_room_temperature"

    # An entity that is not exposed to the user does not make its area appear.
    other = entities.async_get_or_create("switch", "test", "3", suggested_object_id="office_fan")
    entities.async_update_entity(other.entity_id, area_id=hidden.id)

    reply = await _areas(anton_client)

    assert reply["success"]
    assert reply["result"] == {
        "floors": [{"floor_id": ground.floor_id, "name": "Ground floor", "level": 0}],
        "areas": [
            {
                "area_id": garage.id,
                "name": "Garage",
                "floor_id": ground.floor_id,
                "entity_count": 1,
            },
            {"area_id": living.id, "name": "Living room", "floor_id": None, "entity_count": 1},
        ],
    }


@pytest.mark.usefixtures("demo_states")
async def test_unconfigured_user_gets_no_areas(
    hass: HomeAssistant,
    hass_ws_client: Callable[..., Coroutine[Any, Any, Any]],
    setup_bridge: SetupBridge,
) -> None:
    ar.async_get(hass).async_create("Garage")
    await setup_bridge(CONFIG)
    admin_client = await hass_ws_client(hass)

    reply = await _areas(admin_client)

    assert reply["result"] == {"floors": [], "areas": []}

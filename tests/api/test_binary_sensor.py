"""Tests for binary sensors: listed read-only, never controllable (concept 8.6, 11.4)."""

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

CONFIG = {
    "users": [
        {
            "username": "anton",
            "filter": {"include_entities": ["binary_sensor.front_door", "binary_sensor.motion"]},
        }
    ]
}


@pytest.fixture
async def client(
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    client_for: Callable[[User], Coroutine[Any, Any, Any]],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> Any:
    """Return a client for anton, who may see two of three binary sensors."""
    hass.states.async_set("binary_sensor.front_door", "off", {"device_class": "door"})
    hass.states.async_set("binary_sensor.motion", "on", {"device_class": "motion"})
    hass.states.async_set("binary_sensor.bedroom_presence", "on", {"device_class": "presence"})
    anton = add_user("anton")
    await setup_bridge(CONFIG)
    return await client_for(anton)


async def test_binary_sensors_are_listed_with_their_class(client: Any) -> None:
    await client.send_json_auto_id({"type": "haac_bridge/entities/list"})
    reply = await client.receive_json()

    by_id = {entity["entity_id"]: entity for entity in reply["result"]["entities"]}
    assert set(by_id) == {"binary_sensor.front_door", "binary_sensor.motion"}
    assert by_id["binary_sensor.front_door"]["domain"] == "binary_sensor"
    assert by_id["binary_sensor.front_door"]["device_class"] == "door"
    assert by_id["binary_sensor.motion"]["state"] == "on"


async def test_binary_sensor_cannot_be_controlled(hass: HomeAssistant, client: Any) -> None:
    calls = async_mock_service(hass, "binary_sensor", "turn_on")
    await client.send_json_auto_id(
        {
            "type": "haac_bridge/call_service",
            "entity_id": "binary_sensor.motion",
            "service": "turn_on",
            "service_data": {},
        }
    )
    reply = await client.receive_json()

    assert reply["error"]["code"] == "HAB-SVC-002"
    assert calls == []

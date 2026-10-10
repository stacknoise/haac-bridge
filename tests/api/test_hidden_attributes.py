"""Attributes that name other entities or carry an access link never reach the app (finding S5)."""

from collections.abc import Callable, Coroutine
from datetime import timedelta
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util
import pytest
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.haac_bridge.entities.attributes import is_hidden

SENSOR = "sensor.house_max_temperature"
ATTRIBUTES = {
    "unit_of_measurement": "°C",
    "friendly_name": "House max",
    "entity_id": ["sensor.bedroom_temperature", "sensor.office_temperature"],
    "max_entity_id": "sensor.office_temperature",
    "entity_picture": "/api/camera_proxy/camera.door?token=secret",
}
VISIBLE = {"unit_of_measurement": "°C", "friendly_name": "House max"}


@pytest.fixture
async def client(
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    client_for: Callable[[User], Coroutine[Any, Any, Any]],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> Any:
    """Return a client for anton, who sees only the max sensor."""
    anton = add_user("anton")
    hass.states.async_set(SENSOR, "22.5", ATTRIBUTES)
    await setup_bridge({"users": [{"username": "anton", "filter": {"include_entities": [SENSOR]}}]})
    return await client_for(anton)


async def _send(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    """Send a command and return its reply."""
    await client.send_json_auto_id(message)
    return await client.receive_json()


@pytest.mark.parametrize(
    ("name", "hidden"),
    [
        ("entity_id", True),
        ("entities", True),
        ("min_entity_id", True),
        ("entity_picture", True),
        ("access_token", True),
        ("unit_of_measurement", False),
        ("hvac_modes", False),
        ("entity_count", False),
    ],
)
def test_which_attributes_are_hidden(name: str, hidden: bool) -> None:
    assert is_hidden(name) is hidden


async def test_the_entity_list_leaves_them_out(client: Any) -> None:
    reply = await _send(client, {"type": "haac_bridge/entities/list"})
    (entity,) = reply["result"]["entities"]
    assert entity["attributes"] == VISIBLE


async def test_live_events_leave_them_out(hass: HomeAssistant, client: Any) -> None:
    reply = await _send(client, {"type": "haac_bridge/subscribe_entities"})
    assert reply["success"]
    initial = (await client.receive_json())["event"]
    assert initial["a"][SENSOR]["a"] == VISIBLE

    hass.states.async_set(
        SENSOR,
        "23.0",
        {**ATTRIBUTES, "max_entity_id": "sensor.bedroom_temperature", "friendly_name": "Max"},
    )
    change = (await client.receive_json())["event"]["c"][SENSOR]
    assert change["+"]["s"] == "23.0"
    assert change["+"]["a"] == {"friendly_name": "Max"}
    assert "-" not in change


async def test_a_change_of_hidden_attributes_only_sends_no_attributes(
    hass: HomeAssistant, client: Any
) -> None:
    await _send(client, {"type": "haac_bridge/subscribe_entities"})
    await client.receive_json()

    hass.states.async_set(SENSOR, "22.5", {**ATTRIBUTES, "max_entity_id": "sensor.cellar"})
    change = (await client.receive_json())["event"]["c"][SENSOR]
    assert "a" not in change["+"]


async def test_history_leaves_them_out(hass: HomeAssistant, client: Any) -> None:
    await async_wait_recording_done(hass)
    reply = await _send(
        client,
        {
            "type": "haac_bridge/history",
            "entity_ids": [SENSOR],
            "start": (dt_util.utcnow() - timedelta(hours=1)).isoformat(),
        },
    )
    rows = reply["result"][SENSOR]
    assert rows
    assert all(not any(is_hidden(name) for name in row.get("a", {})) for row in rows)
    assert rows[0]["a"] == VISIBLE

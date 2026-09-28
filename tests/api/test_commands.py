"""Tests for haac_bridge/info, exposure/revision and entities/list (concept 11.2)."""

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.auth.models import User
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import instance_id
import pytest

SetupBridge = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

CONFIG = {
    "entity_config": {"switch.garage_socket": {"name": "Garage"}},
    "users": [
        {
            "username": "anton",
            "filter": {
                "include_entities": ["switch.garage_socket", "sensor.living_room_temperature"],
            },
        }
    ],
}


async def _call(client: Any, command: str) -> dict[str, Any]:
    """Send a command and return its reply."""
    await client.send_json_auto_id({"type": command})
    return await client.receive_json()


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


async def test_info(hass: HomeAssistant, anton_client: Any) -> None:
    await hass.config.async_update(
        internal_url="http://192.168.1.10:8123", external_url="https://ha.example.com"
    )

    reply = await _call(anton_client, "haac_bridge/info")
    assert reply["success"]
    assert reply["result"] == {
        "bridge_version": "0.1.0",
        "api_version": 1,
        "domains": ["climate", "sensor", "switch"],
        "ha_version": HA_VERSION,
        "instance_id": await instance_id.async_get(hass),
        "urls": {
            "internal": "http://192.168.1.10:8123",
            "external": "https://ha.example.com",
            "cloud": None,
        },
    }


async def test_info_without_external_address(hass: HomeAssistant, anton_client: Any) -> None:
    await hass.config.async_update(internal_url="http://192.168.1.10:8123", external_url=None)

    urls = (await _call(anton_client, "haac_bridge/info"))["result"]["urls"]
    assert urls == {"internal": "http://192.168.1.10:8123", "external": None, "cloud": None}


@pytest.mark.usefixtures("demo_states")
async def test_entities_list_and_revision(anton_client: Any) -> None:
    listing = (await _call(anton_client, "haac_bridge/entities/list"))["result"]
    revision = (await _call(anton_client, "haac_bridge/exposure/revision"))["result"]

    assert revision == {"revision": listing["revision"], "entity_count": 2}
    by_id = {entity["entity_id"]: entity for entity in listing["entities"]}
    assert set(by_id) == {"sensor.living_room_temperature", "switch.garage_socket"}

    sensor = by_id["sensor.living_room_temperature"]
    assert sensor["domain"] == "sensor"
    assert sensor["state"] == "21.4"
    assert sensor["device_class"] == "temperature"
    assert sensor["unit_of_measurement"] == "°C"
    assert sensor["state_class"] == "measurement"
    assert sensor["attributes"]["unit_of_measurement"] == "°C"
    assert by_id["switch.garage_socket"]["device_class"] == "outlet"
    assert by_id["switch.garage_socket"]["name"] == "garage socket"
    assert by_id["switch.garage_socket"]["configured_name"] == "Garage"
    assert sensor["configured_name"] is None


@pytest.mark.usefixtures("demo_states")
async def test_unconfigured_user_sees_nothing(
    hass: HomeAssistant,
    hass_ws_client: Callable[..., Coroutine[Any, Any, Any]],
    setup_bridge: SetupBridge,
) -> None:
    await setup_bridge(CONFIG)
    admin_client = await hass_ws_client(hass)

    listing = (await _call(admin_client, "haac_bridge/entities/list"))["result"]
    revision = (await _call(admin_client, "haac_bridge/exposure/revision"))["result"]
    assert listing["entities"] == []
    assert revision["entity_count"] == 0

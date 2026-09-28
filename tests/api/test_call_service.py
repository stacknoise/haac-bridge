"""Tests for haac_bridge/call_service (concept 10.3, 11.4, 14.2)."""

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

CONFIG = {
    "users": [
        {
            "username": "anton",
            "filter": {"include_entities": ["switch.garage_socket", "switch.ghost"]},
        }
    ]
}


@pytest.fixture
async def client(
    add_user: Callable[[str], User],
    client_for: Callable[[User], Coroutine[Any, Any, Any]],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    demo_states: None,
) -> Any:
    """Return a client for anton, who may control switch.garage_socket only."""
    anton = add_user("anton")
    await setup_bridge(CONFIG)
    return await client_for(anton)


async def _call_service(client: Any, entity_id: str, service: str, **data: Any) -> dict[str, Any]:
    """Send haac_bridge/call_service and return the reply."""
    await client.send_json_auto_id(
        {
            "type": "haac_bridge/call_service",
            "entity_id": entity_id,
            "service": service,
            "service_data": data,
        }
    )
    return await client.receive_json()


async def test_exposed_entity_is_called_as_the_user(hass: HomeAssistant, client: Any) -> None:
    calls = async_mock_service(hass, "switch", "turn_off")
    reply = await _call_service(client, "switch.garage_socket", "turn_off")

    assert reply["success"], reply
    assert len(calls) == 1
    assert calls[0].data["entity_id"] in ("switch.garage_socket", ["switch.garage_socket"])
    assert calls[0].context.user_id is not None


async def test_not_exposed_entity_is_rejected(hass: HomeAssistant, client: Any) -> None:
    calls = async_mock_service(hass, "switch", "turn_off")
    reply = await _call_service(client, "switch.office_fan", "turn_off")

    assert reply["error"]["code"] == "HAB-SVC-001"
    assert calls == []


async def test_service_of_another_domain_is_rejected(hass: HomeAssistant, client: Any) -> None:
    async_mock_service(hass, "climate", "set_temperature")
    reply = await _call_service(client, "switch.garage_socket", "set_temperature")

    assert reply["error"]["code"] == "HAB-SVC-002"


async def test_missing_entity_is_reported(hass: HomeAssistant, client: Any) -> None:
    async_mock_service(hass, "switch", "turn_off")
    reply = await _call_service(client, "switch.ghost", "turn_off")

    assert reply["error"]["code"] == "HAB-ENT-001"


@pytest.mark.parametrize("key", ["entity_id", "device_id", "area_id"])
async def test_target_in_service_data_is_rejected(
    hass: HomeAssistant, client: Any, key: str
) -> None:
    calls = async_mock_service(hass, "switch", "turn_off")
    reply = await _call_service(
        client, "switch.garage_socket", "turn_off", **{key: "switch.office_fan"}
    )

    assert reply["error"]["code"] == "HAB-WS-001"
    assert calls == []


async def test_failing_service_is_reported(hass: HomeAssistant, client: Any) -> None:
    async def _fail(call: ServiceCall) -> None:
        raise HomeAssistantError("device offline")

    hass.services.async_register("switch", "turn_on", _fail)
    reply = await _call_service(client, "switch.garage_socket", "turn_on")

    assert reply["error"]["code"] == "HAB-SVC-003"
    assert "offline" not in reply["error"]["message"]

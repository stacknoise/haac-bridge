"""Tests for haac_bridge/call_service (concept 10.3, 11.4, 14.2)."""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import patch

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


async def _call_service(
    client: Any, entity_id: str, service: str, service_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Send haac_bridge/call_service and return the reply."""
    await client.send_json_auto_id(
        {
            "type": "haac_bridge/call_service",
            "entity_id": entity_id,
            "service": service,
            "service_data": service_data or {},
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
        client, "switch.garage_socket", "turn_off", {key: "switch.office_fan"}
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


async def test_a_hanging_service_times_out(hass: HomeAssistant, client: Any) -> None:
    async def _hang(call: ServiceCall) -> None:
        await asyncio.sleep(3600)

    hass.services.async_register("switch", "turn_on", _hang)
    with patch("custom_components.haac_bridge.services.call_factory.SERVICE_TIMEOUT", 0.05):
        reply = await asyncio.wait_for(
            _call_service(client, "switch.garage_socket", "turn_on"), timeout=5
        )

    assert reply["error"]["code"] == "HAB-SVC-003"


async def test_a_service_outside_the_allowlist_is_rejected(
    hass: HomeAssistant, client: Any
) -> None:
    calls = async_mock_service(hass, "switch", "factory_reset")
    reply = await _call_service(client, "switch.garage_socket", "factory_reset")

    assert reply["error"]["code"] == "HAB-SVC-002"
    assert calls == []


async def test_unknown_service_data_is_rejected(hass: HomeAssistant, client: Any) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    reply = await _call_service(client, "switch.garage_socket", "turn_on", {"brightness": 255})

    assert reply["error"]["code"] == "HAB-WS-001"
    assert calls == []


async def test_toggle_stays_allowed_for_switches(hass: HomeAssistant, client: Any) -> None:
    calls = async_mock_service(hass, "switch", "toggle")
    reply = await _call_service(client, "switch.garage_socket", "toggle")

    assert reply["success"], reply
    assert len(calls) == 1


CLIMATE_CALLS = [
    ("turn_on", {}),
    ("turn_off", {}),
    ("set_hvac_mode", {"hvac_mode": "heat"}),
    ("set_temperature", {"temperature": 21.5}),
    ("set_temperature", {"target_temp_low": 19.0, "target_temp_high": 23.0}),
    ("set_humidity", {"humidity": 45}),
    ("set_fan_mode", {"fan_mode": "auto"}),
    ("set_preset_mode", {"preset_mode": "eco"}),
    ("set_swing_mode", {"swing_mode": "on"}),
    ("set_swing_horizontal_mode", {"swing_horizontal_mode": "on"}),
]
"""Every climate call the app makes (haac-android ServiceCallFactory)."""


@pytest.fixture
async def climate_client(
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    client_for: Callable[[User], Coroutine[Any, Any, Any]],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> Any:
    """Return a client for maria, who may control climate.living_room."""
    maria = add_user("maria")
    hass.states.async_set("climate.living_room", "heat", {"temperature": 21})
    await setup_bridge(
        {"users": [{"username": "maria", "filter": {"include_entities": ["climate.living_room"]}}]}
    )
    return await client_for(maria)


@pytest.mark.parametrize(("service", "data"), CLIMATE_CALLS)
async def test_every_climate_call_of_the_app_is_allowed(
    hass: HomeAssistant, climate_client: Any, service: str, data: dict[str, Any]
) -> None:
    calls = async_mock_service(hass, "climate", service)
    reply = await _call_service(climate_client, "climate.living_room", service, data)

    assert reply["success"], reply
    assert len(calls) == 1
    assert {key: calls[0].data[key] for key in data} == data


@pytest.mark.parametrize(
    ("service", "data"),
    [
        ("set_temperature", {"temperature": 21, "hvac_mode": "cool"}),
        ("set_fan_mode", {"preset_mode": "eco"}),
        ("set_aux_heat", {"aux_heat": True}),
    ],
)
async def test_other_climate_calls_are_rejected(
    hass: HomeAssistant, climate_client: Any, service: str, data: dict[str, Any]
) -> None:
    calls = async_mock_service(hass, "climate", service)
    reply = await _call_service(climate_client, "climate.living_room", service, data)

    assert not reply["success"]
    assert reply["error"]["code"] in ("HAB-SVC-002", "HAB-WS-001")
    assert calls == []

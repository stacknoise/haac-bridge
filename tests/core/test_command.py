"""Tests for the command wrapper (concept 18.3)."""

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.core import HomeAssistant
import voluptuous as vol

from custom_components.haac_bridge.core.command import async_register_commands, bridge_command
from custom_components.haac_bridge.core.errors import ErrorCode, InvalidServiceError


@bridge_command("haac_bridge/test/echo", {vol.Required("value"): int})
async def _echo(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> dict[str, Any]:
    return {"value": msg["value"]}


@bridge_command("haac_bridge/test/rejected")
async def _rejected(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    raise InvalidServiceError(ErrorCode.SVC_NOT_ALLOWED)


@bridge_command("haac_bridge/test/crash")
async def _crash(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    raise RuntimeError("boom")


async def test_wrapper_replies_and_maps_errors(
    hass: HomeAssistant,
    hass_ws_client: Callable[..., Coroutine[Any, Any, Any]],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    await setup_bridge({})
    async_register_commands(hass, (_echo, _rejected, _crash))
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "haac_bridge/test/echo", "value": 3})
    reply = await client.receive_json()
    assert reply["success"]
    assert reply["result"] == {"value": 3}

    await client.send_json_auto_id({"type": "haac_bridge/test/echo", "value": "x"})
    reply = await client.receive_json()
    assert reply["error"]["code"] == "HAB-WS-001"

    await client.send_json_auto_id({"type": "haac_bridge/test/rejected"})
    reply = await client.receive_json()
    assert reply["error"]["code"] == "HAB-SVC-001"
    assert reply["error"]["message"] == "You are not allowed to control this device"

    await client.send_json_auto_id({"type": "haac_bridge/test/crash"})
    reply = await client.receive_json()
    assert reply["error"]["code"] == "HAB-INT-000"
    assert "boom" not in reply["error"]["message"]

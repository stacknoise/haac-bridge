"""Tests for the log and Activity entries of haac_bridge/call_service (concept 21.3, 21.4)."""

from typing import Any

from homeassistant.core import Event, HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from .conftest import CLIENT


async def _call(socket: Any, entity_id: str, service: str, **fields: Any) -> dict[str, Any]:
    """Send haac_bridge/call_service and return the reply."""
    await socket.send_json_auto_id(
        {"type": "haac_bridge/call_service", "entity_id": entity_id, "service": service, **fields}
    )
    return await socket.receive_json()


async def test_a_call_is_logged_and_shown_in_activity(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    activity: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited()
    client = await app_client()

    calls = async_mock_service(hass, "switch", "turn_on")

    reply = await _call(client, "switch.garage_socket", "turn_on", client="Pixel 8")
    await hass.async_block_till_done()

    assert reply["success"], reply
    [line] = [r.message for r in caplog.records if r.message.startswith("action=call_service")]
    assert "source=app" in line
    assert 'client="Pixel 8"' in line
    assert "entity=switch.garage_socket" in line
    assert "service=turn_on" in line
    assert "result=ok" in line
    [event] = activity
    assert event.data["entity_id"] == "switch.garage_socket"
    assert event.data["client"] == "Pixel 8"
    assert event.data["source"] == "app"
    assert event.context.id == calls[0].context.id
    assert event.context.user_id is not None


async def test_the_default_level_writes_no_action_line(
    hass: HomeAssistant,
    anton: Any,
    setup_bridge: Any,
    demo_states: None,
    app_client: CLIENT,
    activity: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_bridge(
        {"users": [{"user_id": anton.id, "filter": {"include_domains": ["switch"]}}]}
    )
    client = await app_client()

    async_mock_service(hass, "switch", "turn_on")

    assert (await _call(client, "switch.garage_socket", "turn_on"))["success"]
    await hass.async_block_till_done()

    assert not [r for r in caplog.records if r.message.startswith("action=")]
    assert len(activity) == 1


async def test_the_activity_switch_can_be_turned_off(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    activity: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited(activity=False)
    client = await app_client()

    async_mock_service(hass, "switch", "turn_on")

    assert (await _call(client, "switch.garage_socket", "turn_on"))["success"]
    await hass.async_block_till_done()

    assert activity == []
    assert [r for r in caplog.records if r.message.startswith("action=call_service")]


async def test_a_refusal_is_logged_once_and_not_shown_in_activity(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    activity: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited()
    client = await app_client()

    async_mock_service(hass, "switch", "turn_off")

    reply = await _call(client, "light.kitchen", "turn_on", client="Pixel 8")

    assert reply["error"]["code"] == "HAB-SVC-001"
    errors = [
        r.message
        for r in caplog.records
        if r.name.startswith("custom_components.haac_bridge") and "HAB-SVC-001" in r.message
    ]
    assert len(errors) == 1
    assert "light.kitchen" in errors[0]
    assert 'client="Pixel 8"' in errors[0]
    assert activity == []


async def test_a_failing_service_is_logged_once_and_shown_in_activity(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    activity: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def _fail(call: ServiceCall) -> None:
        raise HomeAssistantError("device offline")

    await setup_audited()
    client = await app_client()

    hass.services.async_register("switch", "turn_on", _fail)

    reply = await _call(client, "switch.garage_socket", "turn_on")
    await hass.async_block_till_done()

    assert reply["error"]["code"] == "HAB-SVC-003"
    errors = [
        r
        for r in caplog.records
        if r.name.startswith("custom_components.haac_bridge") and "HAB-SVC-003" in r.message
    ]
    assert len(errors) == 1
    [event] = activity
    assert event.data["result"] == "failed"


@pytest.mark.parametrize("name", ["", "x" * 41, "bad\nname", 5])
async def test_an_invalid_device_name_is_rejected(
    hass: HomeAssistant, setup_audited: CLIENT, app_client: CLIENT, name: Any
) -> None:
    await setup_audited()
    client = await app_client()

    calls = async_mock_service(hass, "switch", "turn_on")

    reply = await _call(client, "switch.garage_socket", "turn_on", client=name)

    assert not reply["success"]
    assert calls == []


async def test_a_call_from_another_login_has_the_source_other(
    hass: HomeAssistant,
    anton: Any,
    setup_audited: CLIENT,
    client_for: CLIENT,
    activity: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited()

    async_mock_service(hass, "switch", "turn_on")
    client = await client_for(anton)

    assert (await _call(client, "switch.garage_socket", "turn_on"))["success"]
    await hass.async_block_till_done()

    assert activity[0].data["source"] == "other"
    assert any("source=other" in r.message for r in caplog.records)


async def test_debug_logs_every_command(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited(level="debug")
    client = await app_client()

    await client.send_json_auto_id({"type": "haac_bridge/info"})
    await client.receive_json()

    assert any(r.message.startswith("action=command") for r in caplog.records)

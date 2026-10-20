"""Tests for the log and Activity entries of schedule runs and changes (concept 21.3, 21.4)."""

from typing import Any

from homeassistant.core import Event, HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.haac_bridge.core.runtime import get_data

from .conftest import CLIENT

CREATE: dict[str, Any] = {
    "type": "haac_bridge/schedules/create",
    "name": "Morning light",
    "when": {"type": "time", "time": "06:45", "days": [0, 1, 2, 3, 4]},
    "action": "turn_on",
    "entities": ["switch.garage_socket"],
}


async def _send(socket: Any, **message: Any) -> dict[str, Any]:
    """Send a command and return its reply."""
    await socket.send_json_auto_id(message)
    reply = await socket.receive_json()
    assert reply["success"], reply
    return reply["result"]


def _lines(caplog: pytest.LogCaptureFixture, action: str) -> list[str]:
    """Return the audit log lines of one action."""
    return [r.message for r in caplog.records if r.message.startswith(f"action={action}")]


async def test_a_manual_run_is_logged_with_who_started_it(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    activity: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited()
    client = await app_client()

    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await _send(client, **CREATE)

    await _send(
        client, type="haac_bridge/schedules/run_now", schedule_id=schedule["id"], client="Pixel 8"
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    assert len(calls) == 1
    [switched] = _lines(caplog, "schedule_run")
    assert 'schedule="Morning light"' in switched
    assert "trigger=manual" in switched
    assert 'client="Pixel 8"' in switched
    [result] = _lines(caplog, "schedule_result")
    assert "result=ok" in result
    assert "entities=1/1" in result or 'entities="1/1"' in result
    [event] = activity
    assert event.data["action"] == "schedule_run"
    assert "name" not in event.data
    assert "Morning light" not in str(event.data)
    assert event.context.id == calls[0].context.id


async def test_a_failed_entity_reaches_activity_but_not_the_info_log(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    activity: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited()
    client = await app_client()
    schedule = await _send(client, **CREATE)
    hass.states.async_remove("switch.garage_socket")

    await get_data(hass).schedules.runner.async_run(schedule["id"])

    assert _lines(caplog, "schedule_run") == []
    assert "result=failed" in _lines(caplog, "schedule_result")[0]


async def test_schedule_changes_are_logged(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited()
    client = await app_client()
    schedule = await _send(client, **CREATE)
    await _send(
        client,
        type="haac_bridge/schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        enabled=False,
    )
    await _send(client, type="haac_bridge/schedules/delete", schedule_id=schedule["id"])

    changes = _lines(caplog, "schedule_change")
    assert [line.split()[1] for line in changes] == [
        "change=created",
        "change=updated",
        "change=deleted",
    ]
    assert "fields=enabled" in changes[1]


async def test_deactivating_an_entity_is_logged(
    hass: HomeAssistant,
    setup_audited: CLIENT,
    app_client: CLIENT,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await setup_audited()
    client = await app_client()

    await _send(
        client,
        type="haac_bridge/entities/set_disabled",
        entity_id="switch.garage_socket",
        disabled=True,
    )

    [line] = _lines(caplog, "entity_disabled")
    assert "entity=switch.garage_socket" in line

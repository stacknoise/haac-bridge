"""Tests for haac_bridge/subscribe_entities and exposure_changed (concept 9.2, 11.2, 14.2)."""

from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haac_bridge.config.schema import CONFIG_SCHEMA

SECTION = {
    "users": [
        {
            "username": "anton",
            "filter": {
                "include_entities": ["switch.garage_socket"],
                "include_entity_globs": ["sensor.*_humidity"],
            },
        }
    ]
}


@pytest.fixture
async def subscribed(
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    client_for: Callable[[User], Coroutine[Any, Any, Any]],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    demo_states: None,
) -> tuple[Any, dict[str, Any]]:
    """Subscribe as anton; return the client and the initial event."""
    anton = add_user("anton")
    await setup_bridge(SECTION)
    client = await client_for(anton)
    await client.send_json_auto_id({"type": "haac_bridge/subscribe_entities"})
    reply = await client.receive_json()
    assert reply["success"], reply
    assert reply["result"] is None
    initial = await client.receive_json()
    assert initial["type"] == "event"
    return client, initial["event"]


async def _revision(client: Any) -> str:
    """Return the caller's current revision."""
    await client.send_json_auto_id({"type": "haac_bridge/exposure/revision"})
    return (await client.receive_json())["result"]["revision"]


async def test_initial_event_holds_exposed_states_only(
    subscribed: tuple[Any, dict[str, Any]],
) -> None:
    _, initial = subscribed
    assert set(initial["a"]) == {"switch.garage_socket", "sensor.bath_humidity"}
    assert initial["a"]["switch.garage_socket"]["s"] == "on"


async def test_changes_of_exposed_entities_only(
    hass: HomeAssistant, subscribed: tuple[Any, dict[str, Any]]
) -> None:
    client, _ = subscribed
    hass.states.async_set("switch.office_fan", "on")  # not exposed: no event
    hass.states.async_set("switch.garage_socket", "off")
    event = (await client.receive_json())["event"]
    assert event["c"]["switch.garage_socket"]["+"]["s"] == "off"


async def test_new_and_removed_entities_change_the_exposure(
    hass: HomeAssistant, subscribed: tuple[Any, dict[str, Any]]
) -> None:
    client, _ = subscribed
    before = await _revision(client)

    hass.states.async_set("sensor.cellar_humidity", "70")
    assert "sensor.cellar_humidity" in (await client.receive_json())["event"]["a"]
    changed = (await client.receive_json())["event"]["exposure_changed"]
    assert changed["revision"] == await _revision(client) != before

    hass.states.async_remove("sensor.cellar_humidity")
    assert (await client.receive_json())["event"]["r"] == ["sensor.cellar_humidity"]
    assert (await client.receive_json())["event"]["exposure_changed"]["revision"] == before


async def test_reload_sends_exposure_changed(
    hass: HomeAssistant, subscribed: tuple[Any, dict[str, Any]]
) -> None:
    client, _ = subscribed
    new_config = CONFIG_SCHEMA(
        {
            "haac_bridge": {
                "users": [
                    {"username": "anton", "filter": {"include_entities": ["switch.office_fan"]}}
                ]
            }
        }
    )
    with patch(
        "custom_components.haac_bridge.async_integration_yaml_config", return_value=new_config
    ):
        await hass.services.async_call("haac_bridge", "reload", blocking=True)

    assert set((await client.receive_json())["event"]["a"]) == {"switch.office_fan"}
    assert set((await client.receive_json())["event"]["r"]) == {
        "sensor.bath_humidity",
        "switch.garage_socket",
    }
    changed = (await client.receive_json())["event"]["exposure_changed"]
    assert changed["revision"] == await _revision(client)


async def test_reload_with_new_names_changes_the_revision(
    hass: HomeAssistant, subscribed: tuple[Any, dict[str, Any]]
) -> None:
    client, _ = subscribed
    before = await _revision(client)
    new_config = CONFIG_SCHEMA(
        {"haac_bridge": {**SECTION, "entity_config": {"switch.garage_socket": {"name": "Garage"}}}}
    )
    with patch(
        "custom_components.haac_bridge.async_integration_yaml_config", return_value=new_config
    ):
        await hass.services.async_call("haac_bridge", "reload", blocking=True)

    changed = (await client.receive_json())["event"]["exposure_changed"]
    assert changed["revision"] == await _revision(client) != before


async def test_a_second_subscription_replaces_the_first(
    hass: HomeAssistant, subscribed: tuple[Any, dict[str, Any]]
) -> None:
    client, _ = subscribed
    await client.send_json_auto_id({"type": "haac_bridge/subscribe_entities"})
    reply = await client.receive_json()
    assert reply["success"], reply
    second_id = reply["id"]
    await client.receive_json()  # initial states of the second subscription

    hass.states.async_set("switch.garage_socket", "off")
    message = await client.receive_json()
    assert message["id"] == second_id
    assert message["event"]["c"]["switch.garage_socket"]["+"]["s"] == "off"

    # Only one entity subscription is left, so the next change arrives once.
    hass.states.async_set("switch.garage_socket", "on")
    await hass.async_block_till_done()
    message = await client.receive_json()
    assert message["id"] == second_id
    await client.send_json_auto_id({"type": "haac_bridge/exposure/revision"})
    assert (await client.receive_json())["type"] == "result"

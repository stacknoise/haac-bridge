"""Tests for setup and the haac_bridge.reload action (concept 10.2, 18.4)."""

from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
import pytest

from custom_components.haac_bridge.core.errors import ConfigError
from custom_components.haac_bridge.core.runtime import get_data

SetupBridge = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]
YAML_CONFIG = "custom_components.haac_bridge.async_integration_yaml_config"


def _config(*entities: str) -> dict[str, Any]:
    """Return a haac_bridge config exposing the given entities to anton."""
    return {
        "haac_bridge": {
            "users": [{"username": "anton", "filter": {"include_entities": list(entities)}}]
        }
    }


@pytest.mark.usefixtures("demo_states")
async def test_reload_applies_new_exposure_and_clears_issues(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
    add_user: Callable[[str], User],
    setup_bridge: SetupBridge,
) -> None:
    anton = add_user("anton")
    await setup_bridge(
        {
            "users": [
                {"username": "anton", "filter": {"include_entities": ["switch.garage_socket"]}},
                {"username": "nobody"},
            ]
        }
    )
    assert issue_registry.async_get_issue("haac_bridge", "cfg_unknown_user_nobody")

    with patch(YAML_CONFIG, return_value=_config("switch.office_fan")):
        await hass.services.async_call("haac_bridge", "reload", blocking=True)

    assert get_data(hass).exposure.exposed_entity_ids(hass, anton) == ["switch.office_fan"]
    assert issue_registry.async_get_issue("haac_bridge", "cfg_unknown_user_nobody") is None


@pytest.mark.usefixtures("demo_states")
async def test_invalid_reload_keeps_previous_config(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
    add_user: Callable[[str], User],
    setup_bridge: SetupBridge,
) -> None:
    anton = add_user("anton")
    await setup_bridge(_config("switch.garage_socket")["haac_bridge"])

    with patch(YAML_CONFIG, return_value=None), pytest.raises(ConfigError):
        await hass.services.async_call("haac_bridge", "reload", blocking=True)

    assert get_data(hass).exposure.exposed_entity_ids(hass, anton) == ["switch.garage_socket"]
    assert issue_registry.async_get_issue("haac_bridge", "cfg_invalid")

    with patch(YAML_CONFIG, return_value=_config("switch.garage_socket")):
        await hass.services.async_call("haac_bridge", "reload", blocking=True)
    assert issue_registry.async_get_issue("haac_bridge", "cfg_invalid") is None

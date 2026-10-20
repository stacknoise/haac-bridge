"""Tests for the logging settings: YAML block, options form and their order (concept 21.2)."""

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haac_bridge.audit.levels import LoggingSettings, LogLevel
from custom_components.haac_bridge.const import DOMAIN, LOGGER_NAME
from custom_components.haac_bridge.core.runtime import get_data


async def _setup(hass: HomeAssistant, section: dict[str, Any], options: dict[str, Any]) -> Any:
    """Set up the bridge from YAML and add a config entry with the given options."""
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: section})
    entry = MockConfigEntry(domain=DOMAIN, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_the_default_level_is_warning(hass: HomeAssistant) -> None:
    await _setup(hass, {}, {})

    assert get_data(hass).audit.settings == LoggingSettings()
    assert logging.getLogger(LOGGER_NAME).level == logging.WARNING
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)


async def test_yaml_wins_over_the_options(hass: HomeAssistant) -> None:
    await _setup(
        hass, {"logging": {"level": "error"}}, {"logging": {"level": "debug", "activity": False}}
    )

    assert get_data(hass).audit.settings == LoggingSettings(LogLevel.ERROR, False)
    assert logging.getLogger(LOGGER_NAME).level == logging.ERROR
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)


async def test_an_invalid_yaml_level_is_a_configuration_error(hass: HomeAssistant) -> None:
    assert not await async_setup_component(hass, DOMAIN, {DOMAIN: {"logging": {"level": "loud"}}})


async def test_the_options_form_saves_and_applies_the_settings(hass: HomeAssistant) -> None:
    entry = await _setup(hass, {}, {"users": []})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "logging"}
    )
    assert result["step_id"] == "logging"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"level": "info", "activity": False}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["logging"] == {"level": "info", "activity": False}
    assert entry.options["users"] == []
    assert get_data(hass).audit.settings == LoggingSettings(LogLevel.INFO, False)
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)


async def test_saving_users_keeps_the_logging_options(
    hass: HomeAssistant, add_user: Callable[..., User]
) -> None:
    anton = add_user("anton")
    options = {"users": [], "logging": {"level": "debug", "activity": True}}
    entry = await _setup(hass, {}, options)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "import_yaml"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"yaml": f"users:\n- user_id: {anton.id}\n  filter:\n    include_domains: [switch]\n"},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["logging"] == {"level": "debug", "activity": True}
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)


async def test_the_yaml_form_names_what_the_yaml_sets(hass: HomeAssistant) -> None:
    entry = await _setup(hass, {"logging": {"level": "info"}}, {})

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "logging"}
    )

    assert result["description_placeholders"] == {"yaml": "level"}
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)


async def test_a_change_of_the_settings_is_logged(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    entry = await _setup(hass, {"logging": {"level": "info"}}, {})
    hass.config_entries.async_update_entry(entry, options={"logging": {"activity": False}})
    await hass.async_block_till_done()

    lines = [r.message for r in caplog.records if r.message.startswith("action=config_change")]
    assert any("what=logging" in line and "activity=false" in line for line in lines)
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)


async def test_the_start_and_a_change_of_the_users_are_logged(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    entry = await _setup(hass, {"logging": {"level": "info"}}, {})
    hass.config_entries.async_update_entry(entry, options={"users": []})
    await hass.async_block_till_done()

    lines = [r.message for r in caplog.records if r.message.startswith("action=")]
    started = [line for line in lines if line.startswith("action=startup")]
    assert started
    assert "api_version=1" in started[0]
    assert "client_info" in started[0]
    assert any(line.startswith("action=config_change what=options") for line in lines)
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)

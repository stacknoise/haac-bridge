"""Tests for the log level and Activity settings (concept 21.2)."""

import logging

import pytest

from custom_components.haac_bridge.audit.levels import (
    LoggingSettings,
    LogLevel,
    apply_level,
    merge_settings,
    yaml_keys,
)
from custom_components.haac_bridge.const import LOGGER_NAME


def test_the_default_is_warning_with_activity() -> None:
    assert merge_settings(None, None) == LoggingSettings(LogLevel.WARNING, True)


def test_an_option_is_used_without_yaml() -> None:
    settings = merge_settings({}, {"level": "debug", "activity": False})
    assert settings == LoggingSettings(LogLevel.DEBUG, False)


def test_yaml_wins_over_the_option_per_key() -> None:
    settings = merge_settings({"level": "error"}, {"level": "debug", "activity": False})
    assert settings == LoggingSettings(LogLevel.ERROR, False)


@pytest.mark.parametrize("damaged", [{"level": "loud"}, {"level": 3}, {"activity": "yes"}])
def test_damaged_values_fall_back(damaged: dict[str, object]) -> None:
    assert merge_settings(damaged, None) == LoggingSettings()
    assert yaml_keys(damaged) == set()


def test_yaml_keys_name_what_the_yaml_sets() -> None:
    assert yaml_keys({"level": "info", "activity": True}) == {"level", "activity"}
    assert yaml_keys(None) == set()


def test_apply_level_sets_the_package_logger() -> None:
    apply_level(LogLevel.DEBUG)
    assert logging.getLogger(LOGGER_NAME).level == logging.DEBUG
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)

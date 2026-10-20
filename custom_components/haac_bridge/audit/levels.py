"""Log level and Activity switch of the bridge: reading, merging and applying them (concept 21.2)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import logging
from typing import Any

from ..const import CONF_ACTIVITY, CONF_LEVEL, DEFAULT_LOG_LEVEL, LOGGER_NAME


class LogLevel(StrEnum):
    """The log levels an administrator can choose."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def number(self) -> int:
        """Return the number of the level in the `logging` module."""
        return logging.getLevelNamesMapping()[self.name]


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """The log level and whether switching actions appear in the Activity page."""

    level: LogLevel = field(default=LogLevel(DEFAULT_LOG_LEVEL))
    activity: bool = True


def _level_of(section: Mapping[str, Any] | None) -> LogLevel | None:
    """Return the level named in a `logging` block, or None if it is missing or damaged."""
    try:
        return LogLevel((section or {}).get(CONF_LEVEL))
    except ValueError:
        return None


def _activity_of(section: Mapping[str, Any] | None) -> bool | None:
    """Return the Activity switch of a `logging` block, or None if it is missing or damaged."""
    value = (section or {}).get(CONF_ACTIVITY)
    return value if isinstance(value, bool) else None


def merge_settings(
    yaml_section: Mapping[str, Any] | None, options_section: Mapping[str, Any] | None
) -> LoggingSettings:
    """Return the settings: a value in the YAML wins over the option, damaged values fall back (concept 21.2)."""
    defaults = LoggingSettings()
    level = _level_of(yaml_section) or _level_of(options_section) or defaults.level
    activity = _activity_of(yaml_section)
    if activity is None:
        activity = _activity_of(options_section)
    return LoggingSettings(level, defaults.activity if activity is None else activity)


def yaml_keys(yaml_section: Mapping[str, Any] | None) -> set[str]:
    """Return which of `level` and `activity` the YAML sets, so the options form can say so."""
    keys = set()
    if _level_of(yaml_section) is not None:
        keys.add(CONF_LEVEL)
    if _activity_of(yaml_section) is not None:
        keys.add(CONF_ACTIVITY)
    return keys


def apply_level(level: LogLevel) -> None:
    """Set the level of the package logger; every module logger of the bridge inherits it."""
    logging.getLogger(LOGGER_NAME).setLevel(level.number)

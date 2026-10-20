"""AuditLog: writes audit entries to the HA log and fires the Activity event (concept 21.3, 21.4)."""

import json
import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant, callback

from ..const import EVENT_ACTION
from .entry import AuditEntry
from .levels import LoggingSettings, apply_level

_LOGGER = logging.getLogger(__package__)

_PLAIN = re.compile(r"^[A-Za-z0-9_.:/@-]+$")
_LINE_BREAKS = str.maketrans({"\u2028": "\\u2028", "\u2029": "\\u2029", "\x85": "\\u0085"})


def format_value(value: Any) -> str:
    """Return a value for a log line: plain words as they are, everything else as JSON.

    JSON escapes line breaks and quotes, so text typed by a user cannot forge a second log line (concept 21.7).
    """
    if value is None:
        return "none"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str) and _PLAIN.match(value):
        return value
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return text.translate(_LINE_BREAKS)


def format_line(entry: AuditEntry) -> str:
    """Return the log line of an entry: `action=… key=value …`."""
    parts = [f"action={entry.action}"]
    parts.extend(f"{key}={format_value(value)}" for key, value in entry.fields)
    return " ".join(parts)


class AuditLog:
    """Records audit entries; the level and the Activity switch come from `configure`."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Start with the default settings."""
        self._hass = hass
        self.settings = LoggingSettings()

    @callback
    def configure(self, settings: LoggingSettings) -> None:
        """Take over new settings and set the level of the package logger."""
        self.settings = settings
        apply_level(settings.level)

    def is_enabled(self, level: int) -> bool:
        """Return whether a line of this level would be written, so callers can skip building it."""
        return _LOGGER.isEnabledFor(level)

    @callback
    def record(self, entry: AuditEntry) -> None:
        """Write the log line and, if the Activity switch is on, fire the event of the entry."""
        if entry.log:
            _LOGGER.log(entry.level, "%s", format_line(entry))
        if entry.activity is not None and self.settings.activity:
            self._hass.bus.async_fire(EVENT_ACTION, entry.activity, context=entry.context)

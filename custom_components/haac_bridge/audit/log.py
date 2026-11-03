"""AuditLog: writes audit entries to the HA log and fires the Activity event (concept 21.3, 21.4)."""

import logging

from homeassistant.core import HomeAssistant, callback

from ..const import EVENT_ACTION
from ..core.formatting import format_value
from .entry import AuditEntry
from .levels import LoggingSettings, apply_level

_LOGGER = logging.getLogger(__package__)


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

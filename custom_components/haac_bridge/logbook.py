"""Describes the `haac_bridge_action` events for the Home Assistant Activity page (concept 21.4)."""

from collections.abc import Callable

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback

from .audit.describe import describe
from .const import DOMAIN, EVENT_ACTION


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, str]]], None],
) -> None:
    """Register how the Activity page shows the events of the bridge."""

    @callback
    def _describe(event: Event) -> dict[str, str]:
        """Return the name, the message and, if known, the entity of one event."""
        entry = {LOGBOOK_ENTRY_NAME: "HAAC Bridge", LOGBOOK_ENTRY_MESSAGE: describe(event.data)}
        if entity_id := event.data.get("entity_id"):
            entry[LOGBOOK_ENTRY_ENTITY_ID] = entity_id
        return entry

    async_describe_event(DOMAIN, EVENT_ACTION, _describe)

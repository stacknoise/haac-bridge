"""Tests for the Activity page entries (concept 21.4)."""

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.core import Event, HomeAssistant

from custom_components.haac_bridge.const import DOMAIN, EVENT_ACTION
from custom_components.haac_bridge.logbook import async_describe_events


def _describe(hass: HomeAssistant) -> dict[str, tuple[str, object]]:
    """Return what the integration registers with the logbook, by event type."""
    registered: dict[str, tuple[str, object]] = {}
    async_describe_events(
        hass, lambda domain, event, func: registered.update({event: (domain, func)})
    )
    return registered


def test_the_event_is_registered_for_the_domain(hass: HomeAssistant) -> None:
    assert _describe(hass)[EVENT_ACTION][0] == DOMAIN


def test_an_entry_names_the_entity_and_the_action(hass: HomeAssistant) -> None:
    describe = _describe(hass)[EVENT_ACTION][1]
    event = Event(
        EVENT_ACTION,
        {
            "action": "call_service",
            "result": "ok",
            "service": "turn_on",
            "entity_id": "switch.garage_socket",
            "source": "app",
            "client": "Pixel 8",
        },
    )

    assert describe(event) == {
        LOGBOOK_ENTRY_NAME: "HAAC Bridge",
        LOGBOOK_ENTRY_MESSAGE: "turned on via HAAC app (Pixel 8)",
        LOGBOOK_ENTRY_ENTITY_ID: "switch.garage_socket",
    }


def test_a_skipped_run_has_no_entity(hass: HomeAssistant) -> None:
    describe = _describe(hass)[EVENT_ACTION][1]
    entry = describe(Event(EVENT_ACTION, {"action": "schedule_skipped", "result": "skipped"}))

    assert LOGBOOK_ENTRY_ENTITY_ID not in entry

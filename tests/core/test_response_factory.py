"""Tests for the WebSocket replies of ResponseFactory (concept 11.3, 18.2)."""

from homeassistant.core import Context, Event, EventStateChangedData, State

from custom_components.haac_bridge.core.response_factory import (
    ResponseFactory,
    _without_hidden_attributes,
)


def _event(attributes: dict[str, object]) -> Event[EventStateChangedData]:
    """Return a state change of a sensor whose new state carries these attributes."""
    return Event(
        "state_changed",
        EventStateChangedData(
            entity_id="sensor.house_max",
            old_state=State("sensor.house_max", "21", attributes),
            new_state=State("sensor.house_max", "22", attributes),
        ),
        context=Context(),
    )


def test_an_event_without_hidden_attributes_is_passed_on_as_it_is() -> None:
    event = _event({"unit_of_measurement": "°C"})
    assert _without_hidden_attributes(event) is event


def test_the_copy_without_hidden_attributes_is_made_once_per_event() -> None:
    """HA caches the serialized diff by event object, so every subscriber must get the same copy."""
    event = _event({"unit_of_measurement": "°C", "max_entity_id": "sensor.office"})
    first = _without_hidden_attributes(event)
    assert first is not event
    assert "max_entity_id" not in (first.data["new_state"] or State("a.b", "")).attributes
    assert _without_hidden_attributes(event) is first
    assert _without_hidden_attributes(_event({"entity_id": ["sensor.a"]})) is not first


def test_subscribers_get_the_same_serialized_event_apart_from_their_id() -> None:
    factory = ResponseFactory()
    event = _event({"unit_of_measurement": "°C", "max_entity_id": "sensor.office"})
    one = factory.state_diff(1, event)
    two = factory.state_diff(2, event)
    assert b"max_entity_id" not in one
    assert one.replace(b'"id":1', b'"id":2') == two

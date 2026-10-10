"""DescriptorFactory: builds the entity descriptors sent to the app (concept 11.3, 18.2)."""

from collections.abc import Callable, Mapping
from typing import Any

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_SUPPORTED_FEATURES,
    ATTR_UNIT_OF_MEASUREMENT,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from ..entities.attributes import shareable_attributes

DomainFields = Callable[[State, er.RegistryEntry | None], dict[str, Any]]


def _no_fields(state: State, entry: er.RegistryEntry | None) -> dict[str, Any]:
    """Return no domain-specific fields (switch, climate: everything is in attributes)."""
    return {}


def _sensor_fields(state: State, entry: er.RegistryEntry | None) -> dict[str, Any]:
    """Return unit, state class and display precision a sensor tile needs (8.3)."""
    options = entry.options.get("sensor", {}) if entry else {}
    return {
        "unit_of_measurement": state.attributes.get(ATTR_UNIT_OF_MEASUREMENT),
        "state_class": state.attributes.get("state_class"),
        "display_precision": options.get(
            "display_precision", options.get("suggested_display_precision")
        ),
    }


_DOMAIN_FIELDS: dict[str, DomainFields] = {
    "switch": _no_fields,
    "sensor": _sensor_fields,
    "climate": _no_fields,
}


class DescriptorFactory:
    """Creates one descriptor per entity; the only place with per-domain field selection."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Keep the registries needed to resolve names and areas."""
        self._hass = hass

    def create(self, state: State, configured_name: str | None = None) -> dict[str, Any]:
        """Return the descriptor of an entity including its current state and all attributes.

        `name` is always HA's friendly name; `configured_name` is the name from `entity_config`
        that the app shows by default (concept 7.3), or None.
        """
        entry = er.async_get(self._hass).async_get(state.entity_id)
        attributes = state.attributes
        descriptor: dict[str, Any] = {
            "entity_id": state.entity_id,
            "domain": state.domain,
            "name": state.name,
            "configured_name": configured_name,
            "device_class": attributes.get(ATTR_DEVICE_CLASS),
            "supported_features": attributes.get(ATTR_SUPPORTED_FEATURES, 0),
            "area": self._area_name(entry),
            "state": state.state,
            "attributes": shareable_attributes(attributes),
            "last_changed": state.last_changed.isoformat(),
            "last_updated": state.last_updated.isoformat(),
        }
        descriptor.update(_DOMAIN_FIELDS.get(state.domain, _no_fields)(state, entry))
        return descriptor

    def create_many(
        self, entity_ids: list[str], names: Mapping[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """Return descriptors with configured names, skipping entities without a state."""
        names = names or {}
        states = (self._hass.states.get(entity_id) for entity_id in entity_ids)
        return [
            self.create(state, names.get(state.entity_id)) for state in states if state is not None
        ]

    def _area_name(self, entry: er.RegistryEntry | None) -> str | None:
        """Return the HA area of the entity, or of its device if the entity has none."""
        if entry is None:
            return None
        area_id = entry.area_id
        if area_id is None and entry.device_id is not None:
            device = dr.async_get(self._hass).async_get(entry.device_id)
            area_id = device.area_id if device else None
        if area_id is None:
            return None
        area = ar.async_get(self._hass).async_get_area(area_id)
        return area.name if area else None

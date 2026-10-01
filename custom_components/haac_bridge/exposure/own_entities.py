"""Recognises the entities HAAC Bridge creates itself, which are never exposed (concept 10.2, 19.5)."""

from collections.abc import Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ..const import DOMAIN


def own_entity_checker(hass: HomeAssistant) -> Callable[[str], bool]:
    """Return a function that tells whether an entity ID belongs to the platform `haac_bridge`."""
    registry = er.async_get(hass)

    def _is_own(entity_id: str) -> bool:
        """Return True if the entity registry lists the entity under the bridge's own platform."""
        entry = registry.async_get(entity_id)
        return entry is not None and entry.platform == DOMAIN

    return _is_own

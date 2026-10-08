"""Recognises the entities HAAC Bridge creates itself, which are never exposed (concept 10.2, 19.5)."""

from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util.hass_dict import HassKey

from ..const import DOMAIN


class _DeletedOwnEntities:
    """Entity IDs of deleted entities of the platform `haac_bridge`, rebuilt after registry changes."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Start empty and follow the entity registry; the set is built on first use."""
        self._registry = er.async_get(hass)
        self._ids: frozenset[str] | None = None
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._async_invalidate)

    @callback
    def _async_invalidate(self, _event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        """Forget the set; an entity was created, removed or changed."""
        self._ids = None

    def contains(self, entity_id: str) -> bool:
        """Return True if a deleted registry entry of the bridge's platform had this entity ID."""
        if self._ids is None:
            self._ids = frozenset(
                entry.entity_id
                for entry in self._registry.deleted_entities.values()
                if entry.platform == DOMAIN
            )
        return entity_id in self._ids


_DELETED_KEY: HassKey[_DeletedOwnEntities] = HassKey(f"{DOMAIN}_deleted_own_entities")
"""Where the one set of deleted own entities of this HA instance is kept."""


def own_entity_checker(hass: HomeAssistant) -> Callable[[str], bool]:
    """Return a function that tells whether an entity ID belongs to the platform `haac_bridge`.

    Deleted entities of the platform count as well, so the history of a removed schedule's
    entities is never exposed (review finding S3).
    """
    registry = er.async_get(hass)
    if (deleted := hass.data.get(_DELETED_KEY)) is None:
        deleted = hass.data[_DELETED_KEY] = _DeletedOwnEntities(hass)

    def _is_own(entity_id: str) -> bool:
        """Return True if the registry lists the entity, now or deleted, under the bridge's platform."""
        entry = registry.async_get(entity_id)
        if entry is not None:
            return entry.platform == DOMAIN
        return deleted.contains(entity_id)

    return _is_own

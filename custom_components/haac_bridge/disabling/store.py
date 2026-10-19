"""Persistent store of the entities each user deactivated, `.storage/haac_bridge.disabled_entities` (concept 7.5)."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from ..const import DISABLED_STORE_KEY, DISABLED_STORE_VERSION


def _readable(raw: object) -> dict[str, dict[str, str]]:
    """Return the `users` part of stored data, leaving out everything that is not user -> entity -> time."""
    if not isinstance(raw, dict):
        return {}
    return {
        user_id: {
            entity_id: since
            for entity_id, since in entities.items()
            if isinstance(entity_id, str) and isinstance(since, str)
        }
        for user_id, entities in raw.items()
        if isinstance(user_id, str) and isinstance(entities, dict)
    }


class DisabledStore:
    """Holds the deactivated entities of all users in memory and writes them after every change."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Create an empty store; call `async_load` before use."""
        self._store: Store[dict[str, Any]] = Store(
            hass, DISABLED_STORE_VERSION, DISABLED_STORE_KEY, private=True
        )
        self._users: dict[str, dict[str, str]] = {}

    async def async_load(self) -> None:
        """Read the deactivated entities from storage."""
        stored = await self._store.async_load() or {}
        self._users = {
            user_id: entities
            for user_id, entities in _readable(stored.get("users")).items()
            if entities
        }

    def is_disabled(self, user_id: str, entity_id: str) -> bool:
        """Return whether the user deactivated the entity."""
        return entity_id in self._users.get(user_id, {})

    def entities_of(self, user_id: str) -> dict[str, str]:
        """Return the user's deactivated entities with the ISO time of the deactivation."""
        return dict(self._users.get(user_id, {}))

    def user_ids(self) -> list[str]:
        """Return the users who have at least one deactivated entity."""
        return list(self._users)

    async def async_set(self, user_id: str, entity_id: str, disabled: bool) -> bool:
        """Deactivate or activate an entity for the user and save; return whether anything changed."""
        if self.is_disabled(user_id, entity_id) == disabled:
            return False
        if disabled:
            self._users.setdefault(user_id, {})[entity_id] = dt_util.utcnow().isoformat()
        else:
            self._forget_entity(user_id, entity_id)
        await self._async_save()
        return True

    async def async_forget_user(self, user_id: str) -> bool:
        """Drop all entries of a user (deleted or no longer configured) and save; return whether there were any."""
        if self._users.pop(user_id, None) is None:
            return False
        await self._async_save()
        return True

    def _forget_entity(self, user_id: str, entity_id: str) -> None:
        """Remove one entry; a user without entries is removed too."""
        entities = self._users[user_id]
        del entities[entity_id]
        if not entities:
            del self._users[user_id]

    async def _async_save(self) -> None:
        """Write all entries to storage now."""
        await self._store.async_save({"users": self._users})

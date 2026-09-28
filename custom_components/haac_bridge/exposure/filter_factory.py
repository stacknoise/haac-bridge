"""FilterFactory: builds the entity filter of each configured user (concept 10.2, 18.2)."""

from collections.abc import Callable
import logging

from homeassistant.helpers.entityfilter import (
    CONF_INCLUDE_DOMAINS,
    CONF_INCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITY_GLOBS,
    convert_filter,
)

from ..config.schema import UserEntry

_LOGGER = logging.getLogger(__name__)

_INCLUDE_KEYS = (CONF_INCLUDE_DOMAINS, CONF_INCLUDE_ENTITIES, CONF_INCLUDE_ENTITY_GLOBS)

EntityPredicate = Callable[[str], bool]


def _deny_all(entity_id: str) -> bool:
    """Expose no entity; used for entries without any include rule."""
    return False


class FilterFactory:
    """Creates entity filters with HA's entityfilter helper, so rules match the HomeKit Bridge."""

    def create(self, entry: UserEntry) -> EntityPredicate:
        """Return the filter for one user entry; without an include rule it exposes nothing."""
        if not any(entry.filter.get(key) for key in _INCLUDE_KEYS):
            _LOGGER.warning(
                "User %s has no include rule in the haac_bridge filter and sees no entities",
                entry.label,
            )
            return _deny_all
        return convert_filter(entry.filter)

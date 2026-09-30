"""Users configured in the Home Assistant UI, stored in the options of the config entry (concept 10.2)."""

from collections.abc import Mapping
from typing import Any

from homeassistant.helpers.entityfilter import (
    CONF_EXCLUDE_DOMAINS,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_ENTITY_GLOBS,
    CONF_INCLUDE_DOMAINS,
    CONF_INCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITY_GLOBS,
)

from ..const import CONF_FILTER, CONF_NAMES, CONF_USER_ID, CONF_USERS
from .schema import UserEntry

FILTER_KEYS = (
    CONF_INCLUDE_DOMAINS,
    CONF_INCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITY_GLOBS,
    CONF_EXCLUDE_DOMAINS,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_ENTITY_GLOBS,
)
"""The filter rules of a user, named like in the YAML `filter` section (concept 10.2)."""

INCLUDE_KEYS = (CONF_INCLUDE_DOMAINS, CONF_INCLUDE_ENTITIES, CONF_INCLUDE_ENTITY_GLOBS)
"""The rules that expose something; a filter without one exposes nothing."""


def user_options(
    user_id: str, rules: Mapping[str, Any], names: Mapping[str, str]
) -> dict[str, Any]:
    """Return the options record of one user: its ID, the non-empty filter rules and the display names."""
    return {
        CONF_USER_ID: user_id,
        CONF_FILTER: {key: list(rules[key]) for key in FILTER_KEYS if rules.get(key)},
        CONF_NAMES: {entity_id: name for entity_id, name in names.items() if name},
    }


def users_of(options: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return the user records of the entry options; empty if none were configured."""
    return list(options.get(CONF_USERS, []))


def parse_ui_users(options: Mapping[str, Any]) -> list[UserEntry]:
    """Return the user entries of the entry options, with all six filter rules present as HA's filter expects.

    They never carry a username, only the stable user ID.
    """
    return [
        UserEntry(
            username=None,
            user_id=record[CONF_USER_ID],
            filter={key: list(record.get(CONF_FILTER, {}).get(key, [])) for key in FILTER_KEYS},
            names=dict(record.get(CONF_NAMES, {})),
        )
        for record in users_of(options)
    ]

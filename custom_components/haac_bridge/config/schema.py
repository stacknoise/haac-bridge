"""YAML schema of the haac_bridge section in configuration.yaml (concept 10.2)."""

from dataclasses import dataclass, field
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entityfilter import (
    BASE_FILTER_SCHEMA,
    CONF_EXCLUDE_ENTITY_GLOBS,
    CONF_INCLUDE_ENTITY_GLOBS,
)
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from ..const import (
    CONF_ENTITY_CONFIG,
    CONF_FILTER,
    CONF_NAME,
    CONF_USER_ID,
    CONF_USERNAME,
    CONF_USERS,
    DOMAIN,
)


def valid_glob(value: str) -> bool:
    """Return True if a wildcard has the form `domain.pattern`, e.g. `sensor.*_humidity`."""
    domain, dot, pattern = value.strip().partition(".")
    return bool(domain and dot and pattern)


def _globs_checked(rules: dict[str, Any]) -> dict[str, Any]:
    """Voluptuous validator: reject a filter whose include or exclude wildcards are not `domain.pattern`."""
    for key in (CONF_INCLUDE_ENTITY_GLOBS, CONF_EXCLUDE_ENTITY_GLOBS):
        for glob in rules.get(key, []):
            if not valid_glob(glob):
                raise vol.Invalid(f"wildcard {glob!r} must look like domain.pattern", path=[key])
    return rules


FILTER_SCHEMA = vol.All(BASE_FILTER_SCHEMA, _globs_checked)
"""HA's filter schema, plus the same wildcard check the options flow applies (finding U6)."""

ENTITY_CONFIG_SCHEMA = vol.Schema(
    {
        cv.entity_id: vol.Schema(
            {vol.Optional(CONF_NAME): vol.All(cv.string, vol.Strip, vol.Length(min=1))}
        )
    }
)
"""Per-entity settings; `name` is the default display name the app shows (concept 7.3)."""

USER_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Exclusive(CONF_USERNAME, "user"): cv.string,
            vol.Exclusive(CONF_USER_ID, "user"): cv.string,
            vol.Optional(CONF_FILTER, default={}): FILTER_SCHEMA,
            vol.Optional(CONF_ENTITY_CONFIG, default={}): ENTITY_CONFIG_SCHEMA,
        }
    ),
    cv.has_at_least_one_key(CONF_USERNAME, CONF_USER_ID),
)


def _none_as_empty(section: Any) -> Any:
    """Return an empty section for a bare `haac_bridge:` line, which YAML reads as None."""
    return {} if section is None else section


SECTION_SCHEMA = vol.All(
    _none_as_empty,
    vol.Schema(
        {
            vol.Optional(CONF_ENTITY_CONFIG, default={}): ENTITY_CONFIG_SCHEMA,
            vol.Optional(CONF_USERS, default=[]): vol.All(cv.ensure_list, [USER_SCHEMA]),
        }
    ),
)
"""The content of the `haac_bridge:` section; a bare section means no users."""

CONFIG_SCHEMA = vol.Schema({DOMAIN: SECTION_SCHEMA}, extra=vol.ALLOW_EXTRA)


@dataclass(frozen=True, slots=True)
class UserEntry:
    """One validated entry under `users`: who it applies to, its filter and its entity names."""

    username: str | None
    user_id: str | None
    filter: dict[str, list[str]]
    names: dict[str, str] = field(default_factory=dict)

    @property
    def label(self) -> str:
        """Return the name used for this entry in logs and Repairs."""
        return self.user_id or self.username or "?"


def parse_users(config: ConfigType) -> list[UserEntry]:
    """Return the user entries of a validated configuration; empty if the section is missing.

    Each entry's names are the global `entity_config` names overridden by its own.
    """
    section: dict[str, Any] = config.get(DOMAIN) or {}
    shared = _names(section.get(CONF_ENTITY_CONFIG, {}))
    return [
        UserEntry(
            username=entry.get(CONF_USERNAME),
            user_id=entry.get(CONF_USER_ID),
            filter=entry[CONF_FILTER],
            names=shared | _names(entry.get(CONF_ENTITY_CONFIG, {})),
        )
        for entry in section.get(CONF_USERS, [])
    ]


def _names(entity_config: dict[str, dict[str, str]]) -> dict[str, str]:
    """Return entity ID to configured name for the entities that have a name."""
    return {
        entity_id: settings[CONF_NAME]
        for entity_id, settings in entity_config.items()
        if CONF_NAME in settings
    }

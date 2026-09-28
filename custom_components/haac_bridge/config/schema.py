"""YAML schema of the haac_bridge section in configuration.yaml (concept 10.2)."""

from dataclasses import dataclass
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entityfilter import BASE_FILTER_SCHEMA
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from ..const import CONF_FILTER, CONF_USER_ID, CONF_USERNAME, CONF_USERS, DOMAIN

USER_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Exclusive(CONF_USERNAME, "user"): cv.string,
            vol.Exclusive(CONF_USER_ID, "user"): cv.string,
            vol.Optional(CONF_FILTER, default={}): BASE_FILTER_SCHEMA,
        }
    ),
    cv.has_at_least_one_key(CONF_USERNAME, CONF_USER_ID),
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {vol.Optional(CONF_USERS, default=[]): vol.All(cv.ensure_list, [USER_SCHEMA])}
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(frozen=True, slots=True)
class UserEntry:
    """One validated entry under `users`: who it applies to and its filter settings."""

    username: str | None
    user_id: str | None
    filter: dict[str, list[str]]

    @property
    def label(self) -> str:
        """Return the name used for this entry in logs and Repairs."""
        return self.user_id or self.username or "?"


def parse_users(config: ConfigType) -> list[UserEntry]:
    """Return the user entries of a validated configuration; empty if the section is missing."""
    section: dict[str, Any] = config.get(DOMAIN) or {}
    return [
        UserEntry(
            username=entry.get(CONF_USERNAME),
            user_id=entry.get(CONF_USER_ID),
            filter=entry[CONF_FILTER],
        )
        for entry in section.get(CONF_USERS, [])
    ]

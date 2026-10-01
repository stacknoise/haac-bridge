"""Export and import of the users configured in the UI as YAML (concept 10.2)."""

from collections.abc import Mapping
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.yaml import dump, parse_yaml
import voluptuous as vol

from ..const import (
    CONF_ENTITY_CONFIG,
    CONF_FILTER,
    CONF_NAME,
    CONF_NAMES,
    CONF_USER_ID,
    CONF_USERS,
    DOMAIN,
)
from .schema import SECTION_SCHEMA, UserEntry, parse_users
from .ui_users import INCLUDE_KEYS, user_options, users_of


def export_users(options: Mapping[str, Any]) -> str:
    """Return the UI users as the `haac_bridge:` section of a configuration.yaml.

    The result can be pasted into configuration.yaml or into the import of another installation.
    """
    users: list[dict[str, Any]] = []
    for record in users_of(options):
        entry: dict[str, Any] = {
            CONF_USER_ID: record[CONF_USER_ID],
            CONF_FILTER: {key: list(rules) for key, rules in record.get(CONF_FILTER, {}).items()},
        }
        if names := record.get(CONF_NAMES):
            entry[CONF_ENTITY_CONFIG] = {
                entity_id: {CONF_NAME: name} for entity_id, name in sorted(names.items())
            }
        users.append(entry)
    return dump({DOMAIN: {CONF_USERS: users}})


def import_users(text: str) -> tuple[list[dict[str, Any]], str | None]:
    """Return the options records of the users in YAML [text], or the key of the error that stops the import.

    The text may be a whole `haac_bridge:` section or only its content. Users are named by `user_id`;
    each needs at least one include rule, like in the UI. Names come from `entity_config`.
    """
    section = _section_of(text)
    if section is None:
        return [], "invalid_yaml"
    try:
        validated = SECTION_SCHEMA(section)
    except vol.Invalid:
        return [], "invalid_config"
    entries = parse_users({DOMAIN: validated})
    if problem := _problem(entries):
        return [], problem
    return [user_options(str(e.user_id), e.filter, e.names) for e in entries], None


def _section_of(text: str) -> dict[str, Any] | None:
    """Return the `haac_bridge:` content of YAML [text] (or the text itself when it has no such key), or None."""
    try:
        data = parse_yaml(text)
    except HomeAssistantError:
        return None
    section = data.get(DOMAIN, data) if isinstance(data, dict) else None
    return section if isinstance(section, dict) else None


def _problem(entries: list[UserEntry]) -> str | None:
    """Return the key of the first reason the entries cannot become UI users, or None."""
    if not entries:
        return "no_users"
    if any(entry.user_id is None for entry in entries):
        return "needs_user_id"
    if any(not any(entry.filter.get(key) for key in INCLUDE_KEYS) for entry in entries):
        return "no_include"
    return None

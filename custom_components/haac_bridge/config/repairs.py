"""Reports configuration errors (HAB-CFG-*) in the log and in HA Repairs (concept 18.4)."""

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import slugify

from ..const import DOMAIN
from ..core.errors import ErrorCode
from .schema import UserEntry
from .users import async_find_unknown_entries, entry_matches

_LOGGER = logging.getLogger(__name__)

_ISSUE_INVALID = ErrorCode.CFG_INVALID.translation_key


@callback
def async_report_invalid_config(hass: HomeAssistant, issue_ids: set[str]) -> None:
    """Log HAB-CFG-001 and create its Repairs issue; the previous configuration stays active."""
    _LOGGER.error(
        "%s: the haac_bridge configuration is invalid, keeping the previous one",
        ErrorCode.CFG_INVALID,
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        _ISSUE_INVALID,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ErrorCode.CFG_INVALID.translation_key,
    )
    issue_ids.add(_ISSUE_INVALID)


async def async_check_users(
    hass: HomeAssistant,
    issue_ids: set[str],
    entries: list[UserEntry],
    yaml_entries: list[UserEntry],
) -> None:
    """Report entries without a HA user (HAB-CFG-002), YAML duplicates (HAB-CFG-003); remove resolved issues.

    A user in both YAML and the UI is no duplicate: the YAML entry wins by design (concept 10.2).
    """
    current = await _async_report_duplicates(hass, yaml_entries)
    for entry in await async_find_unknown_entries(hass, entries):
        _LOGGER.warning(
            "%s: haac_bridge user %s does not exist in Home Assistant",
            ErrorCode.CFG_UNKNOWN_USER,
            entry.label,
        )
        issue_id = f"{ErrorCode.CFG_UNKNOWN_USER.translation_key}_{slugify(entry.label)}"
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ErrorCode.CFG_UNKNOWN_USER.translation_key,
            translation_placeholders={"user": entry.label},
        )
        current.add(issue_id)
    for issue_id in issue_ids - current:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
    issue_ids.clear()
    issue_ids.update(current)


async def _async_report_duplicates(hass: HomeAssistant, yaml_entries: list[UserEntry]) -> set[str]:
    """Create a HAB-CFG-003 issue for every HA user with more than one YAML entry; return the issue ids.

    The first entry is used, the others are ignored (by `username` and by `user_id` alike).
    """
    issue_ids: set[str] = set()
    for user in await hass.auth.async_get_users():
        matching = [entry for entry in yaml_entries if entry_matches(entry, user)]
        if len(matching) < 2:
            continue
        label = user.name or user.id
        _LOGGER.warning(
            "%s: %d haac_bridge entries refer to user %s; only the first one is used",
            ErrorCode.CFG_DUPLICATE_USER,
            len(matching),
            label,
        )
        issue_id = f"{ErrorCode.CFG_DUPLICATE_USER.translation_key}_{slugify(user.id)}"
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ErrorCode.CFG_DUPLICATE_USER.translation_key,
            translation_placeholders={"user": label, "count": str(len(matching))},
        )
        issue_ids.add(issue_id)
    return issue_ids

"""Reports configuration errors (HAB-CFG-*) in the log and in HA Repairs (concept 18.4)."""

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import slugify

from ..const import DOMAIN
from ..core.errors import ErrorCode
from .schema import UserEntry
from .users import async_find_unknown_entries

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
    hass: HomeAssistant, issue_ids: set[str], entries: list[UserEntry]
) -> None:
    """Report entries without a matching HA user (HAB-CFG-002) and remove resolved issues."""
    current: set[str] = set()
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

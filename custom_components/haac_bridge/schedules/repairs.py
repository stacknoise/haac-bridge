"""Reports stored schedules that could not be read in HA Repairs (concept 19.2)."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from ..const import DOMAIN
from ..core.errors import ErrorCode

ISSUE_UNREADABLE = "sch_unreadable"


@callback
def async_sync_unreadable_issue(hass: HomeAssistant, count: int) -> None:
    """Create the Repairs issue for `count` unreadable stored schedules, or remove it if there are none."""
    if count == 0:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_UNREADABLE)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_UNREADABLE,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_UNREADABLE,
        translation_placeholders={"count": str(count), "code": ErrorCode.SCH_INVALID.value},
    )

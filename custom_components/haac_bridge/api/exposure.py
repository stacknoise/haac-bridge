"""Command haac_bridge/exposure/revision (concept 11.2)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant

from ..core.caller import require_user
from ..core.command import bridge_command
from ..core.runtime import get_data


@bridge_command("haac_bridge/exposure/revision")
async def ws_exposure_revision(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return the revision hash and entity count of the caller's exposed set."""
    snapshot = get_data(hass).exposure.snapshot(hass, require_user(connection))
    return {"revision": snapshot.revision, "entity_count": len(snapshot.entity_ids)}

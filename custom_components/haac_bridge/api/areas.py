"""Command haac_bridge/areas (concept 6.3, 11.2)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant

from ..areas.catalog import area_catalog
from ..core.caller import require_user
from ..core.command import bridge_command
from ..core.runtime import get_data


@bridge_command("haac_bridge/areas")
async def ws_areas(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return the HA floors and areas that hold entities exposed to the caller."""
    snapshot = get_data(hass).exposure.snapshot(hass, require_user(connection))
    return area_catalog(hass, snapshot.entity_ids)

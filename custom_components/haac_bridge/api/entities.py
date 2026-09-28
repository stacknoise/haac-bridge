"""Command haac_bridge/entities/list (concept 11.2, 11.3)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant

from ..core.caller import require_user
from ..core.command import bridge_command
from ..core.runtime import get_data


@bridge_command("haac_bridge/entities/list")
async def ws_entities_list(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return the revision and the descriptors of all entities exposed to the caller."""
    data = get_data(hass)
    snapshot = data.exposure.snapshot(hass, require_user(connection))
    return {
        "revision": snapshot.revision,
        "entities": data.descriptors.create_many(snapshot.entity_ids),
    }

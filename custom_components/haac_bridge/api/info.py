"""Command haac_bridge/info (concept 11.2, 11.4)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant

from ..const import API_VERSION, FEATURES, SUPPORTED_DOMAINS
from ..core.caller import require_user
from ..core.command import bridge_command
from ..core.runtime import get_data
from ..instance.addresses import async_instance_identity


@bridge_command("haac_bridge/info")
async def ws_info(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return bridge, API and HA version, supported domains, instance ID and addresses."""
    require_user(connection)
    return {
        "bridge_version": get_data(hass).version,
        "api_version": API_VERSION,
        "domains": list(SUPPORTED_DOMAINS),
        "features": list(FEATURES),
        "ha_version": HA_VERSION,
        **await async_instance_identity(hass),
    }

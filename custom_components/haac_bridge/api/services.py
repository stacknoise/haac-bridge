"""Command haac_bridge/call_service (concept 10.3, 11.2, 11.4)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from ..core.caller import require_user
from ..core.command import bridge_command
from ..core.runtime import get_data
from ..services.call_factory import async_execute


@bridge_command(
    "haac_bridge/call_service",
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("service"): cv.slug,
        vol.Optional("service_data", default=dict): dict,
    },
)
async def ws_call_service(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Call a service of an exposed entity's domain on that entity only."""
    data = get_data(hass)
    call = data.services.create(
        data.exposure,
        require_user(connection),
        msg["entity_id"],
        msg["service"],
        msg["service_data"],
    )
    await async_execute(hass, call)

"""Command haac_bridge/call_service (concept 10.3, 11.2, 11.4)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from ..audit.actions import ServiceRequest, async_audited_call
from ..audit.client import CLIENT_FIELD, source_of
from ..core.caller import require_user
from ..core.command import bridge_command


@bridge_command(
    "haac_bridge/call_service",
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("service"): cv.slug,
        vol.Optional("service_data", default=dict): dict,
        vol.Optional("client"): CLIENT_FIELD,
    },
)
async def ws_call_service(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Call a service of an exposed entity's domain on that entity only, and record it (concept 21)."""
    request = ServiceRequest(
        entity_id=msg["entity_id"],
        service=msg["service"],
        service_data=msg["service_data"],
        source=source_of(hass, connection),
        client=msg.get("client"),
    )
    await async_audited_call(hass, require_user(connection), request)

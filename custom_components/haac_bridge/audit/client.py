"""The device name the app sends and the source of a call (concept 21.3, 21.5)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant
import voluptuous as vol

from ..const import APP_CLIENT_ID, MAX_CLIENT_LENGTH


def _printable(value: str) -> str:
    """Voluptuous validator: reject a device name with control characters."""
    if not value.isprintable():
        raise vol.Invalid("the device name has control characters")
    return value


CLIENT_FIELD: Any = vol.All(str, vol.Strip, vol.Length(min=1, max=MAX_CLIENT_LENGTH), _printable)
"""Request field `client`: the device name, 1 to 40 printable characters (concept 21.5)."""


def source_of(hass: HomeAssistant, connection: ActiveConnection) -> str:
    """Return `app` if the connection's refresh token belongs to the HAAC app, else `other`."""
    token = hass.auth.async_get_refresh_token(connection.refresh_token_id)
    return "app" if token is not None and token.client_id == APP_CLIENT_ID else "other"

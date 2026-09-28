"""Resolves the calling HA user of a WebSocket request (concept 10.3)."""

from homeassistant.auth.models import User
from homeassistant.components.websocket_api import ActiveConnection

from .errors import ErrorCode, NotAllowedError


def require_user(connection: ActiveConnection) -> User:
    """Return the HA user bound to the connection's access token, never a user named by the client."""
    user = connection.user
    if user is None:
        raise NotAllowedError(ErrorCode.AUTH_NO_USER)
    return user

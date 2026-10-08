"""Resolves the calling HA user of a WebSocket request (concept 10.3)."""

from homeassistant.auth.models import User
from homeassistant.components.websocket_api import ActiveConnection

from .errors import ErrorCode, NotAllowedError


def require_user(connection: ActiveConnection) -> User:
    """Return the HA user bound to the connection's access token, never a user named by the client.

    A deactivated user is refused (HAB-AUTH-002). Home Assistant also closes the user's
    connections when it deactivates them, which ends running subscriptions.
    """
    user = connection.user
    if user is None:
        raise NotAllowedError(ErrorCode.AUTH_NO_USER)
    if not user.is_active:
        raise NotAllowedError(ErrorCode.AUTH_INACTIVE)
    return user

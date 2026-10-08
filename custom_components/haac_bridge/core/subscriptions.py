"""Keeps one subscription of each kind per WebSocket connection (review finding S7)."""

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import callback


@callback
def async_end_subscriptions_of(connection: ActiveConnection, owner_type: type) -> None:
    """End every subscription of the connection whose stop callback belongs to an `owner_type` object.

    Called before a new subscription of that kind starts, so a connection never holds more than
    one; the app opens one per kind and session anyway.
    """
    for msg_id, unsub in list(connection.subscriptions.items()):
        if isinstance(getattr(unsub, "__self__", None), owner_type):
            connection.subscriptions.pop(msg_id)()

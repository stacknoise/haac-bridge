"""ResponseFactory: builds every WebSocket reply of HAAC Bridge (concept 11, 18.2)."""

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import cached_state_diff_message
from homeassistant.core import Event, EventStateChangedData

from .errors import HaacBridgeError


class ResponseFactory:
    """Creates result and error messages in HA's WebSocket reply format."""

    def result(self, msg_id: int, payload: Any) -> dict[str, Any]:
        """Return a success reply carrying `payload`."""
        return websocket_api.result_message(msg_id, payload)

    def event(self, msg_id: int, payload: Any) -> dict[str, Any]:
        """Return an event message of the subscription `msg_id`."""
        return websocket_api.event_message(msg_id, payload)

    def state_diff(self, msg_id: int, event: Event[EventStateChangedData]) -> bytes:
        """Return a state change as HA's compressed diff event, serialized once for all subscribers."""
        return cached_state_diff_message(str(msg_id).encode(), event)

    def error(self, msg_id: int, error: HaacBridgeError) -> dict[str, Any]:
        """Return an error reply whose `code` is the HAB code of `error`."""
        return websocket_api.error_message(
            msg_id,
            error.code.value,
            str(error),
            translation_key=error.translation_key,
            translation_domain=error.translation_domain,
            translation_placeholders=error.translation_placeholders,
        )

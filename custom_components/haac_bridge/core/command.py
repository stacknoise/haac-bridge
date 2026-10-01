"""Command wrapper: every haac_bridge/* command runs through it (concept 18.3)."""

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .errors import ErrorCode
from .runtime import get_data

_LOGGER = logging.getLogger(__name__)

CommandHandler = Callable[[HomeAssistant, ActiveConnection, dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class SubscriptionStarted:
    """Returned by a subscription handler: reply with an empty result, then send `initial` as first event (if any)."""

    initial: Any = None


@dataclass(frozen=True, slots=True)
class BridgeCommand:
    """A haac_bridge/* command: its type, request fields and handler."""

    type: str
    handler: CommandHandler
    fields: dict[Any, Any] = field(default_factory=dict)


def bridge_command(
    command_type: str, fields: dict[Any, Any] | None = None
) -> Callable[[CommandHandler], BridgeCommand]:
    """Declare a handler as haac_bridge/* command with optional request fields."""

    def decorator(handler: CommandHandler) -> BridgeCommand:
        """Wrap the handler into a BridgeCommand."""
        return BridgeCommand(command_type, handler, fields or {})

    return decorator


def async_register_commands(hass: HomeAssistant, commands: Iterable[BridgeCommand]) -> None:
    """Register all commands with HA's WebSocket API, each inside the wrapper."""
    for command in commands:
        transport_schema = vol.Schema(
            {
                vol.Required("id"): cv.positive_int,
                vol.Required("type"): command.type,
            },
            extra=vol.ALLOW_EXTRA,
        )
        websocket_api.async_register_command(hass, command.type, _wrap(command), transport_schema)


def _wrap(command: BridgeCommand) -> websocket_api.WebSocketCommandHandler:
    """Build the HA handler that validates, runs and answers one command."""
    request_schema = vol.Schema(
        {
            vol.Required("id"): cv.positive_int,
            vol.Required("type"): command.type,
            **command.fields,
        }
    )

    @websocket_api.async_response
    async def _handle(
        hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
    ) -> None:
        """Run the command and send exactly one reply (plus the first event of a subscription)."""
        data = get_data(hass)
        try:
            payload = await command.handler(hass, connection, request_schema(msg))
        except Exception as err:  # noqa: BLE001 - the only broad catch allowed (18.3)
            error = data.errors.from_exception(err)
            _log_error(command.type, connection, error.code, err)
            connection.send_message(data.responses.error(msg["id"], error))
            return
        if isinstance(payload, SubscriptionStarted):
            connection.send_message(data.responses.result(msg["id"], None))
            if payload.initial is not None:
                connection.send_message(data.responses.event(msg["id"], payload.initial))
            return
        connection.send_message(data.responses.result(msg["id"], payload))

    return _handle


def _log_error(
    command_type: str,
    connection: ActiveConnection,
    code: ErrorCode,
    err: Exception,
) -> None:
    """Log a failed command once with its HAB code; tracebacks only for unexpected errors."""
    user_id = connection.user.id if connection.user else None
    if code is ErrorCode.INT_UNEXPECTED:
        _LOGGER.error("%s in %s (user %s)", code, command_type, user_id, exc_info=err)
    else:
        cause = f" (cause: {err.__cause__!r})" if err.__cause__ else ""
        _LOGGER.warning("%s in %s (user %s): %s%s", code, command_type, user_id, err, cause)

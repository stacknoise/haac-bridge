"""Commands haac_bridge/history and haac_bridge/statistics (concept 10.3, 11.2)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from ..const import MAX_HISTORY_ENTITIES
from ..core.caller import require_user
from ..core.command import bridge_command
from ..core.runtime import get_data
from ..history.queries import (
    PERIODS,
    STATISTIC_TYPES,
    TimeRange,
    async_history,
    async_statistics,
    utc_datetime,
)

PERIOD_FIELDS = {
    vol.Required("entity_ids"): vol.All(
        cv.ensure_list, [cv.entity_id], vol.Length(max=MAX_HISTORY_ENTITIES)
    ),
    vol.Required("start"): utc_datetime,
    vol.Optional("end"): utc_datetime,
}


def _exposed_request(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> tuple[list[str], TimeRange]:
    """Return the requested entities the caller may see (none for a future period) and the period."""
    period = TimeRange(msg["start"], msg.get("end"))
    if period.in_future:
        return [], period
    user = require_user(connection)
    return get_data(hass).exposure.filter_exposed(user, msg["entity_ids"]), period


@bridge_command(
    "haac_bridge/history",
    {**PERIOD_FIELDS, vol.Optional("minimal_response", default=False): bool},
)
async def ws_history(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return the state history of the requested entities that are exposed to the caller."""
    entity_ids, period = _exposed_request(hass, connection, msg)
    if not entity_ids:
        return {}
    return await async_history(hass, entity_ids, period, msg["minimal_response"])


@bridge_command(
    "haac_bridge/statistics",
    {
        **PERIOD_FIELDS,
        vol.Optional("period", default="hour"): vol.In(PERIODS),
        vol.Optional("types", default=list(STATISTIC_TYPES)): vol.All(
            cv.ensure_list, [vol.In(STATISTIC_TYPES)]
        ),
    },
)
async def ws_statistics(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return long-term statistics of the requested entities that are exposed to the caller."""
    entity_ids, period = _exposed_request(hass, connection, msg)
    if not entity_ids:
        return {}
    return await async_statistics(hass, entity_ids, period, msg["period"], msg["types"])

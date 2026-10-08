"""Commands haac_bridge/schedules/* and haac_bridge/subscribe_schedules (concept 11.2, 19.4)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant
import voluptuous as vol

from ..core.caller import require_user
from ..core.command import SubscriptionStarted, bridge_command
from ..core.runtime import get_data
from ..schedules.subscription import ScheduleSubscription

SCHEDULE_FIELDS = {
    vol.Optional("name"): object,
    vol.Optional("when"): object,
    vol.Optional("action"): object,
    vol.Optional("entities"): object,
    vol.Optional("enabled"): object,
}
"""Content of a schedule; checked in detail by the manager so a bad value gives HAB-SCH-001."""


def _fields(msg: dict[str, Any]) -> dict[str, Any]:
    """Return the schedule fields of a request without the transport keys."""
    return {
        key: value
        for key, value in msg.items()
        if key in {"name", "when", "action", "entities", "enabled"}
    }


@bridge_command("haac_bridge/schedules/revision")
async def ws_schedules_revision(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return the revision and scope of the schedules the caller can see."""
    manager = get_data(hass).schedules
    user = require_user(connection)
    return {"revision": manager.revision_for(user), "scope": manager.scope_of(user)}


@bridge_command("haac_bridge/schedules/list")
async def ws_schedules_list(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return the schedules the caller can see, with the next run of each."""
    return await get_data(hass).schedules.async_list(require_user(connection))


@bridge_command(
    "haac_bridge/schedules/create",
    {
        vol.Required("name"): object,
        vol.Required("when"): object,
        vol.Required("action"): object,
        vol.Required("entities"): object,
        vol.Optional("enabled"): object,
    },
)
async def ws_schedules_create(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Create a schedule owned by the caller and return it."""
    manager = get_data(hass).schedules
    user = require_user(connection)
    schedule = await manager.async_create(user, _fields(msg))
    return await manager.async_describe(schedule, user)


@bridge_command(
    "haac_bridge/schedules/update",
    {vol.Required("schedule_id"): str, vol.Required("updated_at"): str, **SCHEDULE_FIELDS},
)
async def ws_schedules_update(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Change a schedule the caller may edit and return it; the version must be the edited one."""
    manager = get_data(hass).schedules
    user = require_user(connection)
    schedule = await manager.async_update(user, msg["schedule_id"], msg["updated_at"], _fields(msg))
    return await manager.async_describe(schedule, user)


@bridge_command("haac_bridge/schedules/delete", {vol.Required("schedule_id"): str})
async def ws_schedules_delete(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete a schedule the caller may edit; an unknown id is not an error."""
    await get_data(hass).schedules.async_delete(require_user(connection), msg["schedule_id"])


@bridge_command("haac_bridge/schedules/run_now", {vol.Required("schedule_id"): str})
async def ws_schedules_run_now(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Start one run of a schedule now without changing its plan; the result follows as an event."""
    await get_data(hass).schedules.async_run_now(require_user(connection), msg["schedule_id"])


@bridge_command("haac_bridge/subscribe_schedules")
async def ws_subscribe_schedules(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> SubscriptionStarted:
    """Subscribe to `schedules_changed` events for the schedules the caller can see."""
    subscription = ScheduleSubscription(hass, connection, msg["id"], require_user(connection))
    subscription.async_start()
    connection.subscriptions[msg["id"]] = subscription.async_stop
    return SubscriptionStarted()

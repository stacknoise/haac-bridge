"""Commands haac_bridge/entities/list, entities/set_disabled and subscribe_entities (concept 7.5, 11.2, 11.3)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from ..core.caller import require_user
from ..core.command import SubscriptionStarted, bridge_command
from ..core.runtime import get_data
from ..disabling.manager import async_set_disabled
from ..entities.subscription import EntitySubscription


@bridge_command("haac_bridge/entities/list")
async def ws_entities_list(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return the revision and the descriptors of all entities exposed to the caller, with `disabled`."""
    data = get_data(hass)
    user = require_user(connection)
    snapshot = data.exposure.snapshot(hass, user)
    deactivated = data.disabled.entities_of(user.id)
    descriptors = data.descriptors.create_many(snapshot.entity_ids, snapshot.names)
    return {
        "revision": snapshot.revision,
        "entities": [
            {**descriptor, "disabled": descriptor["entity_id"] in deactivated}
            for descriptor in descriptors
        ],
    }


@bridge_command(
    "haac_bridge/entities/set_disabled",
    {vol.Required("entity_id"): cv.entity_id, vol.Required("disabled"): bool},
)
async def ws_entities_set_disabled(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Deactivate or activate an exposed entity for the caller; reply with their list and the schedules changed."""
    return await async_set_disabled(
        hass, require_user(connection), msg["entity_id"], disabled=msg["disabled"]
    )


@bridge_command("haac_bridge/subscribe_entities")
async def ws_subscribe_entities(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> SubscriptionStarted:
    """Subscribe to the live states of the caller's exposed entities."""
    subscription = EntitySubscription(hass, connection, msg["id"], require_user(connection))
    initial = subscription.async_start()
    connection.subscriptions[msg["id"]] = subscription.async_stop
    return SubscriptionStarted(initial)

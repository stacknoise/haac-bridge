"""Commands haac_bridge/entities/list and haac_bridge/subscribe_entities (concept 11.2, 11.3)."""

from typing import Any

from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant

from ..core.caller import require_user
from ..core.command import SubscriptionStarted, bridge_command
from ..core.runtime import get_data
from ..entities.subscription import EntitySubscription


@bridge_command("haac_bridge/entities/list")
async def ws_entities_list(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> dict[str, Any]:
    """Return the revision and the descriptors of all entities exposed to the caller."""
    data = get_data(hass)
    snapshot = data.exposure.snapshot(hass, require_user(connection))
    return {
        "revision": snapshot.revision,
        "entities": data.descriptors.create_many(snapshot.entity_ids, snapshot.names),
    }


@bridge_command("haac_bridge/subscribe_entities")
async def ws_subscribe_entities(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> SubscriptionStarted:
    """Subscribe to the live states of the caller's exposed entities."""
    subscription = EntitySubscription(hass, connection, msg["id"], require_user(connection))
    initial = subscription.async_start()
    connection.subscriptions[msg["id"]] = subscription.async_stop
    return SubscriptionStarted(initial)

"""Live state subscription of one app connection (concept 9.2, 11.2).

Events use HA's compressed format (`a` added, `c` changed, `r` removed) and, whenever the
exposed set changes, an `exposure_changed` event with the new revision.
"""

from collections.abc import Callable
from typing import Any

from homeassistant.auth.models import User
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import SIGNAL_EXPOSURE_CHANGED
from ..core.runtime import get_data
from ..core.subscriptions import async_end_subscriptions_of
from ..exposure.exposure import compute_revision

ADDED = "a"
CHANGED = "c"
REMOVED = "r"
EXPOSURE_CHANGED = "exposure_changed"


class EntitySubscription:
    """Sends state changes of the entities exposed to one user to one WebSocket subscription."""

    def __init__(
        self,
        hass: HomeAssistant,
        connection: ActiveConnection,
        msg_id: int,
        user: User,
    ) -> None:
        """Keep everything needed to filter and send events; nothing is subscribed yet."""
        self._hass = hass
        self._connection = connection
        self._msg_id = msg_id
        self._user = user
        self._data = get_data(hass)
        self._entity_ids: set[str] = set()
        self._unsubs: list[Callable[[], None]] = []

    @callback
    def async_start(self) -> dict[str, Any]:
        """Start listening and return the initial event with the states of all exposed entities.

        A previous entity subscription of the same connection ends first (one per connection).
        """
        async_end_subscriptions_of(self._connection, EntitySubscription)
        self._entity_ids = set(self._data.exposure.exposed_entity_ids(self._hass, self._user))
        self._unsubs = [
            self._hass.bus.async_listen(
                EVENT_STATE_CHANGED,
                self._async_on_state_changed,
                event_filter=self._async_is_relevant,
            ),
            async_dispatcher_connect(
                self._hass, SIGNAL_EXPOSURE_CHANGED, self._async_on_exposure_changed
            ),
        ]
        return {ADDED: self._compressed_states(self._entity_ids)}

    @callback
    def async_stop(self) -> None:
        """Stop listening; called by HA when the app unsubscribes or the connection closes."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs = []

    @callback
    def _async_is_relevant(self, event_data: EventStateChangedData) -> bool:
        """Return True for entities already sent to the app or exposed to its user."""
        entity_id = event_data["entity_id"]
        return entity_id in self._entity_ids or self._data.exposure.is_exposed(
            self._user, entity_id
        )

    @callback
    def _async_on_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """Forward a change, or report an entity that appeared in or left the exposed set."""
        entity_id = event.data["entity_id"]
        new_state = event.data["new_state"]
        known = entity_id in self._entity_ids
        exposed = new_state is not None and self._data.exposure.is_exposed(self._user, entity_id)
        if known and exposed:
            self._connection.send_message(self._data.responses.state_diff(self._msg_id, event))
            return
        if exposed:
            self._entity_ids.add(entity_id)
            self._send({ADDED: self._compressed_states({entity_id})})
        else:
            self._entity_ids.discard(entity_id)
            self._send({REMOVED: [entity_id]})
        self._send_exposure_changed()

    @callback
    def _async_on_exposure_changed(self) -> None:
        """After a reload: send entities added to or removed from the set, then the new revision."""
        current = set(self._data.exposure.exposed_entity_ids(self._hass, self._user))
        if added := current - self._entity_ids:
            self._send({ADDED: self._compressed_states(added)})
        if removed := self._entity_ids - current:
            self._send({REMOVED: sorted(removed)})
        self._entity_ids = current
        self._send_exposure_changed()

    def _send_exposure_changed(self) -> None:
        """Tell the app to run its revision check (concept 9.2)."""
        names = self._data.exposure.configured_names(self._user)
        revision = compute_revision(list(self._entity_ids), names)
        self._send({EXPOSURE_CHANGED: {"revision": revision}})

    def _send(self, payload: dict[str, Any]) -> None:
        """Send one event of this subscription."""
        self._connection.send_message(self._data.responses.event(self._msg_id, payload))

    def _compressed_states(self, entity_ids: set[str]) -> dict[str, Any]:
        """Return HA's compressed state for each entity that still has a state."""
        states = (self._hass.states.get(entity_id) for entity_id in sorted(entity_ids))
        return {state.entity_id: state.as_compressed_state for state in states if state is not None}

"""Live subscription of one app connection to schedule changes (concept 19.4)."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.auth.models import User
from homeassistant.components.websocket_api import ActiveConnection
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import SIGNAL_SCHEDULES_CHANGED
from ..core.runtime import get_data

SCHEDULES_CHANGED = "schedules_changed"


class ScheduleSubscription:
    """Sends `schedules_changed` with the new revision whenever the caller's schedules change."""

    def __init__(
        self, hass: HomeAssistant, connection: ActiveConnection, msg_id: int, user: User
    ) -> None:
        """Keep what is needed to compute the revision and send events; nothing is subscribed yet."""
        self._hass = hass
        self._connection = connection
        self._msg_id = msg_id
        self._user = user
        self._revision = ""
        self._unsub: Callable[[], None] | None = None

    @callback
    def async_start(self) -> None:
        """Remember the current revision and start listening."""
        self._revision = get_data(self._hass).schedules.revision_for(self._user)
        self._unsub = async_dispatcher_connect(
            self._hass, SIGNAL_SCHEDULES_CHANGED, self._async_on_changed
        )

    @callback
    def async_stop(self) -> None:
        """Stop listening; called by HA when the app unsubscribes or the connection closes."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    @callback
    def _async_on_changed(self) -> None:
        """Send an event if the caller's view of the schedules changed."""
        data = get_data(self._hass)
        revision = data.schedules.revision_for(self._user)
        if revision == self._revision:
            return
        self._revision = revision
        payload = {SCHEDULES_CHANGED: {"revision": revision}}
        self._connection.send_message(data.responses.event(self._msg_id, payload))

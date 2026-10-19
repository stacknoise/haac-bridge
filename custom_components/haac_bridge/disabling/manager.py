"""Deactivating and activating entities for a user, with the effect on their schedules (concept 7.5)."""

from __future__ import annotations

from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from ..const import DOMAIN, MAX_DISABLED_PER_USER
from ..core.errors import EntityNotFoundError, ErrorCode, RequestError
from ..core.runtime import get_data
from .schedules import changes_for

SIGNAL_DISABLED_CHANGED = f"{DOMAIN}_disabled_changed"
"""Dispatcher signal sent with the user id after that user deactivated or activated an entity."""


def disabled_list(hass: HomeAssistant, user_id: str) -> list[str]:
    """Return the entity ids the user deactivated, sorted; the payload of `disabled` replies and events."""
    return sorted(get_data(hass).disabled.entities_of(user_id))


async def async_set_disabled(
    hass: HomeAssistant, user: User, entity_id: str, *, disabled: bool
) -> dict[str, Any]:
    """Deactivate or activate an entity for the caller; return their full list and the schedules switched.

    The entity must be exposed to the caller (HAB-ENT-001); only an existing deactivation can be lifted
    for an entity that is no longer exposed, so a withdrawn entity never keeps a user at the limit.
    A new deactivation beyond MAX_DISABLED_PER_USER is HAB-WS-001. The schedules of the caller that
    contain the entity are switched off, or on again, and `disabled_changed` goes to all connections.
    """
    data = get_data(hass)
    store = data.disabled
    lifting = not disabled and store.is_disabled(user.id, entity_id)
    if not lifting and not data.exposure.is_exposed(user, entity_id):
        raise EntityNotFoundError(ErrorCode.ENT_NOT_FOUND)
    if (
        disabled
        and not store.is_disabled(user.id, entity_id)
        and len(store.entities_of(user.id)) >= MAX_DISABLED_PER_USER
    ):
        raise RequestError(ErrorCode.WS_INVALID_REQUEST)
    switched: list[str] = []
    if await store.async_set(user.id, entity_id, disabled):
        switched = await _async_follow_in_schedules(hass, user.id, entity_id)
        async_dispatcher_send(hass, SIGNAL_DISABLED_CHANGED, user.id)
    return {"disabled": disabled_list(hass, user.id), "schedules_changed": switched}


async def _async_follow_in_schedules(
    hass: HomeAssistant, user_id: str, entity_id: str
) -> list[str]:
    """Store, re-plan and announce the changes to the user's schedules; return the ids switched."""
    data = get_data(hass)
    schedules = data.schedules
    replace, switched = changes_for(
        data.disabled, schedules.store.by_owner(user_id), entity_id, dt_util.utcnow()
    )
    if replace:
        await schedules.store.async_apply_changes(replace=replace)
        for schedule in replace:
            await schedules.planner.async_plan(schedule.id)
        schedules.notify(*(schedule.id for schedule in replace))
    return switched


async def async_sweep(hass: HomeAssistant) -> None:
    """Drop the entries of users who are gone or no longer configured (concept 19.6.3).

    Does nothing while the UI users are not loaded, like the sweep of the schedules.
    """
    data = get_data(hass)
    if not data.schedules.users_ready:
        return
    for user_id in data.disabled.user_ids():
        user = await hass.auth.async_get_user(user_id)
        if user is None or not data.exposure.is_configured(user):
            await data.disabled.async_forget_user(user_id)

"""Tests for the store of deactivated entities and its cleanup (concept 7.5)."""

from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.haac_bridge.const import DISABLED_STORE_KEY
from custom_components.haac_bridge.core.runtime import get_data
from custom_components.haac_bridge.disabling.manager import async_sweep
from custom_components.haac_bridge.disabling.store import DisabledStore

from ..schedules.conftest import World
from .helpers import FAN, GARAGE


async def test_changes_are_saved_and_read_back(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    store = DisabledStore(hass)
    await store.async_load()
    assert await store.async_set("u1", GARAGE, True)
    assert not await store.async_set("u1", GARAGE, True)
    assert await store.async_set("u2", FAN, True)

    saved = hass_storage[DISABLED_STORE_KEY]["data"]["users"]
    assert set(saved) == {"u1", "u2"}
    assert list(saved["u1"]) == [GARAGE]

    again = DisabledStore(hass)
    await again.async_load()
    assert again.is_disabled("u1", GARAGE)
    assert again.entities_of("u2").keys() == {FAN}
    assert again.user_ids() == ["u1", "u2"]
    assert await again.async_set("u2", FAN, False)
    assert again.user_ids() == ["u1"]


async def test_unreadable_stored_data_is_ignored(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    hass_storage[DISABLED_STORE_KEY] = {
        "version": 1,
        "key": DISABLED_STORE_KEY,
        "data": {"users": {"u1": {GARAGE: "2026-10-19T08:00:00+00:00", FAN: 5}, "u2": 7, "u3": {}}},
    }
    store = DisabledStore(hass)
    await store.async_load()
    assert store.entities_of("u1").keys() == {GARAGE}
    assert store.user_ids() == ["u1"]


async def test_the_entries_of_a_user_can_be_dropped(hass: HomeAssistant) -> None:
    store = DisabledStore(hass)
    await store.async_load()
    await store.async_set("u1", GARAGE, True)
    assert await store.async_forget_user("u1")
    assert not await store.async_forget_user("u1")
    assert store.entities_of("u1") == {}


async def test_the_sweep_drops_users_who_are_gone_or_not_configured(
    hass: HomeAssistant, world: World
) -> None:
    disabled = get_data(hass).disabled
    for user_id in (world.anton.id, world.bob.id, "deleted-user"):
        await disabled.async_set(user_id, GARAGE, True)

    await async_sweep(hass)
    assert disabled.user_ids() == [world.anton.id]


async def test_the_sweep_waits_until_the_users_are_loaded(
    hass: HomeAssistant, world: World
) -> None:
    disabled = get_data(hass).disabled
    await disabled.async_set(world.bob.id, GARAGE, True)
    get_data(hass).schedules.users_ready = False

    await async_sweep(hass)
    assert disabled.user_ids() == [world.bob.id]


async def test_a_deleted_user_loses_the_entries(hass: HomeAssistant, world: World) -> None:
    disabled = get_data(hass).disabled
    await disabled.async_set(world.anton.id, GARAGE, True)
    await hass.auth.async_remove_user(world.anton)
    await hass.async_block_till_done()
    assert disabled.entities_of(world.anton.id) == {}

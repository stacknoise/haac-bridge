"""Tests for the schedule store (concept 19.2)."""

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
import pytest

from custom_components.haac_bridge.core.errors import ErrorCode, ScheduleError
from custom_components.haac_bridge.schedules.store import ScheduleStore

from .conftest import CREATED, make_schedule

KEY = "haac_bridge.schedules"


async def _loaded(hass: HomeAssistant) -> ScheduleStore:
    """Return a loaded store."""
    store = ScheduleStore(hass)
    await store.async_load()
    return store


async def test_add_is_saved_and_survives_a_reload(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    store = await _loaded(hass)
    schedule = make_schedule()
    await store.async_add(schedule)
    assert hass_storage[KEY]["version"] == 1
    assert hass_storage[KEY]["data"]["schedules"][0]["id"] == schedule.id
    assert (await _loaded(hass)).schedules == [schedule]


async def test_empty_storage_gives_an_empty_store(hass: HomeAssistant) -> None:
    assert (await _loaded(hass)).schedules == []


async def test_schedules_are_ordered_by_creation(hass: HomeAssistant) -> None:
    store = await _loaded(hass)
    late = make_schedule(name="Late", created=CREATED + timedelta(hours=2))
    early = make_schedule(name="Early")
    await store.async_add(late)
    await store.async_add(early)
    assert [item.name for item in store.schedules] == ["Early", "Late"]


async def test_get_and_by_owner(hass: HomeAssistant) -> None:
    store = await _loaded(hass)
    mine = make_schedule(owner="me")
    theirs = make_schedule(owner="them")
    await store.async_add(mine)
    await store.async_add(theirs)
    assert store.get(mine.id) == mine
    assert store.get("missing") is None
    assert store.by_owner("me") == [mine]
    assert store.by_owner("nobody") == []


async def test_replace_changes_the_stored_schedule(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    store = await _loaded(hass)
    schedule = make_schedule()
    await store.async_add(schedule)
    await store.async_replace(schedule.with_changes(enabled=False))
    assert store.get(schedule.id) == schedule.with_changes(enabled=False)
    assert hass_storage[KEY]["data"]["schedules"][0]["enabled"] is False


async def test_replace_of_an_unknown_schedule_fails(hass: HomeAssistant) -> None:
    store = await _loaded(hass)
    with pytest.raises(ScheduleError) as error:
        await store.async_replace(make_schedule())
    assert error.value.code is ErrorCode.SCH_NOT_FOUND


async def test_remove_returns_what_was_removed(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    store = await _loaded(hass)
    first = make_schedule(name="First")
    second = make_schedule(name="Second")
    await store.async_add(first)
    await store.async_add(second)
    removed = await store.async_remove([first.id, "unknown"])
    assert removed == [first]
    assert store.schedules == [second]
    assert [item["id"] for item in hass_storage[KEY]["data"]["schedules"]] == [second.id]


async def test_remove_of_nothing_does_not_write(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    store = await _loaded(hass)
    assert await store.async_remove(["unknown"]) == []
    assert KEY not in hass_storage


async def test_damaged_entries_are_skipped(
    hass: HomeAssistant, hass_storage: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    good = make_schedule()
    hass_storage[KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": KEY,
        "data": {"schedules": [good.to_dict(), {"id": "broken"}, "nonsense"]},
    }
    store = await _loaded(hass)
    assert store.schedules == [good]
    assert caplog.text.count("damaged schedule") == 2

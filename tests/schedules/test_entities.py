"""Tests for the HA entities of schedules and the config entry that carries them (concept 19.5)."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.haac_bridge.const import DOMAIN
from custom_components.haac_bridge.core.runtime import get_data
from custom_components.haac_bridge.schedules.entities import (
    SUFFIX_ENABLED,
    SUFFIX_NEXT_RUN,
    schedule_id_of,
    unique_id,
)
from custom_components.haac_bridge.schedules.manager import ScheduleManager
from custom_components.haac_bridge.schedules.model import Schedule

from .conftest import World, make_schedule

FIELDS: dict[str, Any] = {
    "name": "Morning light",
    "when": {"type": "time", "time": "06:45", "days": [0, 1, 2, 3, 4, 5, 6]},
    "action": "turn_on",
    "entities": ["switch.garage_socket"],
}


def manager_of(hass: HomeAssistant) -> ScheduleManager:
    """Return the schedule manager of the bridge."""
    return get_data(hass).schedules


def entry_of(hass: HomeAssistant) -> ConfigEntry:
    """Return the one config entry of the bridge."""
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    return entries[0]


def entity_id(hass: HomeAssistant, platform: str, schedule_id: str, suffix: str) -> str | None:
    """Return the entity id the registry holds for a schedule entity, or None."""
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id(schedule_id, suffix))


def state_of(hass: HomeAssistant, platform: str, schedule_id: str, suffix: str) -> State:
    """Return the state of a schedule entity."""
    found = entity_id(hass, platform, schedule_id, suffix)
    assert found is not None
    state = hass.states.get(found)
    assert state is not None
    return state


async def create(hass: HomeAssistant, world: World, **changes: Any) -> Schedule:
    """Create a schedule for anton through the manager and let the entities appear."""
    schedule = await manager_of(hass).async_create(world.anton, {**FIELDS, **changes})
    await hass.async_block_till_done()
    return schedule


def test_unique_ids_round_trip() -> None:
    for suffix in (SUFFIX_ENABLED, SUFFIX_NEXT_RUN):
        assert schedule_id_of(unique_id("abc123", suffix)) == "abc123"
    assert schedule_id_of("something_else") is None
    assert schedule_id_of("haac_bridge_schedule_abc_other") is None


async def test_a_yaml_only_setup_gets_its_config_entry(hass: HomeAssistant, world: World) -> None:
    entry = entry_of(hass)
    assert entry.title == "HAAC Bridge"
    assert entry.data == {}
    assert (
        dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id) == []
    )  # no schedule yet


async def test_entities_appear_with_the_schedule(hass: HomeAssistant, world: World) -> None:
    schedule = await create(hass, world)

    switch = state_of(hass, "switch", schedule.id, SUFFIX_ENABLED)
    assert switch.state == "on"
    assert switch.name == "HAAC Schedules Morning light (Anton)"

    sensor = state_of(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN)
    planned = manager_of(hass).planner.planned_run(schedule.id)
    assert planned is not None
    assert sensor.state == planned.isoformat()
    assert sensor.name == "HAAC Schedules Morning light (Anton) next run"
    assert sensor.attributes["device_class"] == "timestamp"
    assert sensor.attributes["owner"] == world.anton.id
    assert sensor.attributes["owner_name"] == "Anton"
    assert sensor.attributes["paused_reason"] is None
    assert sensor.attributes["last_run"] is None

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry_of(hass).entry_id)
    assert len(devices) == 1
    device = devices[0]
    assert device.name == "HAAC Schedules"
    assert device.identifiers == {(DOMAIN, "schedules")}
    registry = er.async_get(hass)
    for platform, suffix in (("switch", SUFFIX_ENABLED), ("sensor", SUFFIX_NEXT_RUN)):
        found = entity_id(hass, platform, schedule.id, suffix)
        assert found is not None
        registry_entry = registry.async_get(found)
        assert registry_entry is not None
        assert registry_entry.device_id == device.id


async def test_a_disabled_schedule_has_an_unknown_next_run(
    hass: HomeAssistant, world: World
) -> None:
    schedule = await create(hass, world, enabled=False)
    assert state_of(hass, "switch", schedule.id, SUFFIX_ENABLED).state == "off"
    assert state_of(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN).state == "unknown"


async def test_the_switch_enables_and_disables_the_schedule(
    hass: HomeAssistant, world: World
) -> None:
    schedule = await create(hass, world)
    switch = entity_id(hass, "switch", schedule.id, SUFFIX_ENABLED)
    assert switch is not None

    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    await hass.async_block_till_done()
    stored = manager_of(hass).store.get(schedule.id)
    assert stored is not None
    assert stored.enabled is False
    assert stored.updated_at > schedule.updated_at
    assert manager_of(hass).planner.planned_run(schedule.id) is None
    assert state_of(hass, "switch", schedule.id, SUFFIX_ENABLED).state == "off"
    assert state_of(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN).state == "unknown"

    await hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=True)
    await hass.async_block_till_done()
    assert manager_of(hass).planner.planned_run(schedule.id) is not None
    assert state_of(hass, "switch", schedule.id, SUFFIX_ENABLED).state == "on"
    assert state_of(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN).state != "unknown"


async def test_names_follow_renames(hass: HomeAssistant, world: World) -> None:
    schedule = await create(hass, world)
    await manager_of(hass).async_update(
        world.anton, schedule.id, schedule.updated_at.isoformat(), {"name": "Evening light"}
    )
    await hass.async_block_till_done()
    assert state_of(hass, "switch", schedule.id, SUFFIX_ENABLED).name == (
        "HAAC Schedules Evening light (Anton)"
    )
    assert state_of(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN).name == (
        "HAAC Schedules Evening light (Anton) next run"
    )


async def test_equal_names_of_two_owners_stay_apart(hass: HomeAssistant, world: World) -> None:
    mine = await create(hass, world)
    theirs = await manager_of(hass).async_create(world.root, FIELDS)
    await hass.async_block_till_done()

    assert entity_id(hass, "switch", mine.id, SUFFIX_ENABLED) == (
        "switch.haac_schedules_morning_light_anton"
    )
    assert entity_id(hass, "switch", theirs.id, SUFFIX_ENABLED) == (
        "switch.haac_schedules_morning_light_root"
    )
    assert entity_id(hass, "sensor", theirs.id, SUFFIX_NEXT_RUN) == (
        "sensor.haac_schedules_morning_light_root_next_run"
    )


async def test_entities_go_with_the_schedule(hass: HomeAssistant, world: World) -> None:
    schedule = await create(hass, world)
    switch = entity_id(hass, "switch", schedule.id, SUFFIX_ENABLED)
    sensor = entity_id(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN)
    assert switch is not None
    assert sensor is not None

    await manager_of(hass).async_delete(world.anton, schedule.id)
    await hass.async_block_till_done()
    assert entity_id(hass, "switch", schedule.id, SUFFIX_ENABLED) is None
    assert entity_id(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN) is None
    assert hass.states.get(switch) is None
    assert hass.states.get(sensor) is None


async def test_the_entities_are_never_exposed(hass: HomeAssistant, world: World) -> None:
    schedule = await create(hass, world)
    switch = entity_id(hass, "switch", schedule.id, SUFFIX_ENABLED)
    sensor = entity_id(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN)
    exposure = get_data(hass).exposure
    exposed = exposure.exposed_entity_ids(hass, world.anton)
    assert switch not in exposed
    assert sensor not in exposed
    assert "switch.garage_socket" in exposed
    assert not exposure.is_exposed(world.anton, str(switch))


async def test_a_paused_schedule_shows_its_reason(hass: HomeAssistant, world: World) -> None:
    schedule = make_schedule(owner=world.lena.id, entities=("switch.garage_socket",))
    await manager_of(hass).store.async_add(schedule)
    manager_of(hass).notify()
    await hass.async_block_till_done()

    await manager_of(hass).runner.async_run(schedule.id)
    await hass.async_block_till_done()
    sensor = state_of(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN)
    assert sensor.state == "unknown"
    assert sensor.attributes["paused_reason"] == "no_entities"
    assert state_of(hass, "switch", schedule.id, SUFFIX_ENABLED).state == "on"


async def test_the_last_run_is_an_attribute(hass: HomeAssistant, world: World) -> None:
    async_mock_service(hass, "switch", "turn_on")
    schedule = await create(hass, world)
    await manager_of(hass).runner.async_run(schedule.id)
    await hass.async_block_till_done()

    last_run = state_of(hass, "sensor", schedule.id, SUFFIX_NEXT_RUN).attributes["last_run"]
    assert last_run["result"] == "ok"
    assert last_run["code"] is None


async def test_setup_removes_entities_of_schedules_that_are_gone(
    hass: HomeAssistant, world: World
) -> None:
    entry = entry_of(hass)
    registry = er.async_get(hass)
    orphan = registry.async_get_or_create(
        "switch",
        DOMAIN,
        unique_id("ghost", SUFFIX_ENABLED),
        config_entry=entry,
    )
    foreign = registry.async_get_or_create("switch", "other_platform", "keep_me")

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(orphan.entity_id) is None
    assert registry.async_get(foreign.entity_id) is not None


async def test_removing_the_entry_deletes_the_schedules(hass: HomeAssistant, world: World) -> None:
    schedule = await create(hass, world)
    await hass.config_entries.async_remove(entry_of(hass).entry_id)
    await hass.async_block_till_done()

    assert manager_of(hass).store.schedules == []
    assert manager_of(hass).planner.planned_run(schedule.id) is None


async def test_unloading_the_entry_keeps_the_schedules(hass: HomeAssistant, world: World) -> None:
    schedule = await create(hass, world)
    entry = entry_of(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(schedule.id) is not None
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state_of(hass, "switch", schedule.id, SUFFIX_ENABLED).state == "on"

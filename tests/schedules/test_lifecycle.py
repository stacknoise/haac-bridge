"""Tests for the user lifecycle: deleted, deactivated and unconfigured users (concept 19.6)."""

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import slugify
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.haac_bridge import async_reload
from custom_components.haac_bridge.config.schema import CONFIG_SCHEMA
from custom_components.haac_bridge.const import DOMAIN
from custom_components.haac_bridge.core.errors import ConfigError
from custom_components.haac_bridge.core.runtime import get_data
from custom_components.haac_bridge.schedules.manager import ScheduleManager
from custom_components.haac_bridge.schedules.model import PauseReason, Schedule

from .conftest import World, make_schedule

FIELDS: dict[str, Any] = {
    "name": "Morning light",
    "when": {"type": "time", "time": "06:45", "days": [0, 1, 2, 3, 4, 5, 6]},
    "action": "turn_on",
    "entities": ["switch.garage_socket"],
}
YAML_CONFIG = "custom_components.haac_bridge.async_integration_yaml_config"


def manager_of(hass: HomeAssistant) -> ScheduleManager:
    """Return the schedule manager of the bridge."""
    return get_data(hass).schedules


def entry_of(hass: HomeAssistant) -> ConfigEntry:
    """Return the one config entry of the bridge."""
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    return entries[0]


async def make_ui_user(hass: HomeAssistant, user: User) -> None:
    """Configure a user in the UI (the options of the entry) so that it may own schedules."""
    hass.config_entries.async_update_entry(
        entry_of(hass),
        options={
            "users": [
                *entry_of(hass).options.get("users", []),
                {"user_id": user.id, "filter": {"include_domains": ["switch"]}, "names": {}},
            ]
        },
    )
    await hass.async_block_till_done()


async def create(hass: HomeAssistant, user: User) -> Schedule:
    """Create a schedule for the user through the manager."""
    schedule = await manager_of(hass).async_create(user, FIELDS)
    await hass.async_block_till_done()
    return schedule


async def test_deleting_a_ha_user_removes_schedules_and_the_ui_entry(
    hass: HomeAssistant, world: World, add_user: Callable[..., User]
) -> None:
    carol = add_user("carol")
    await make_ui_user(hass, carol)
    hers = await create(hass, carol)
    mine = await create(hass, world.anton)

    await hass.auth.async_remove_user(carol)
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(hers.id) is None
    assert manager_of(hass).store.get(mine.id) is not None
    assert entry_of(hass).options["users"] == []


async def test_deleting_a_yaml_user_reports_the_entry(hass: HomeAssistant, world: World) -> None:
    schedule = await create(hass, world.anton)
    await hass.auth.async_remove_user(world.anton)
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(schedule.id) is None
    issue_id = f"cfg_unknown_user_{slugify(world.anton.id)}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_a_deactivated_user_pauses_and_a_reactivated_one_resumes(
    hass: HomeAssistant, world: World
) -> None:
    schedule = await create(hass, world.anton)
    other = await create(hass, world.root)
    assert manager_of(hass).planner.planned_run(schedule.id) is not None

    await hass.auth.async_update_user(world.anton, is_active=False)
    await hass.async_block_till_done()
    paused = manager_of(hass).store.get(schedule.id)
    assert paused is not None
    assert paused.paused is not None
    assert paused.paused.reason is PauseReason.OWNER_INACTIVE
    assert manager_of(hass).planner.planned_run(schedule.id) is None
    untouched = manager_of(hass).store.get(other.id)
    assert untouched is not None
    assert untouched.paused is None

    await hass.auth.async_update_user(world.anton, is_active=True)
    await hass.async_block_till_done()
    resumed = manager_of(hass).store.get(schedule.id)
    assert resumed is not None
    assert resumed.paused is None
    assert manager_of(hass).planner.planned_run(schedule.id) is not None


async def test_dropping_a_user_from_the_yaml_deletes_the_schedules_at_once(
    hass: HomeAssistant, world: World
) -> None:
    mine = await create(hass, world.anton)
    root = await create(hass, world.root)
    config = CONFIG_SCHEMA(
        {
            "haac_bridge": {
                "users": [
                    {"user_id": world.root.id, "filter": {"include_domains": ["switch"]}},
                ]
            }
        }
    )
    with patch(YAML_CONFIG, return_value=config):
        await async_reload(hass)
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(mine.id) is None
    assert manager_of(hass).store.get(root.id) is not None


async def test_a_rejected_reload_deletes_nothing(hass: HomeAssistant, world: World) -> None:
    schedule = await create(hass, world.anton)
    with patch(YAML_CONFIG, return_value=None), pytest.raises(ConfigError):
        await async_reload(hass)
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(schedule.id) is not None


async def test_removing_a_user_in_the_options_asks_for_a_confirmation(
    hass: HomeAssistant, world: World, add_user: Callable[..., User]
) -> None:
    carol = add_user("carol")
    await make_ui_user(hass, carol)
    await create(hass, carol)
    await create(hass, carol)
    kept = await create(hass, world.anton)

    result = await hass.config_entries.options.async_init(entry_of(hass).entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_user"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": carol.id}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm_remove"
    assert result["description_placeholders"] == {"user": "Carol", "count": "2"}
    assert (
        manager_of(hass).store.by_owner(carol.id) != []
    )  # nothing happens before the confirmation

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert manager_of(hass).store.by_owner(carol.id) == []
    assert manager_of(hass).store.get(kept.id) is not None
    assert entry_of(hass).options["users"] == []


async def test_removing_a_user_without_schedules_needs_no_confirmation(
    hass: HomeAssistant, world: World, add_user: Callable[..., User]
) -> None:
    dave = add_user("dave")
    await make_ui_user(hass, dave)

    result = await hass.config_entries.options.async_init(entry_of(hass).entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "remove_user"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": dave.id}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_setup_deletes_schedules_of_users_who_are_not_configured(
    hass: HomeAssistant, world: World
) -> None:
    stray = make_schedule(owner=world.bob.id)
    await manager_of(hass).store.async_add(stray)
    kept = await create(hass, world.anton)

    assert await hass.config_entries.async_reload(entry_of(hass).entry_id)
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(stray.id) is None
    assert manager_of(hass).store.get(kept.id) is not None


async def test_a_run_waits_while_the_entry_reloads(hass: HomeAssistant, world: World) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await create(hass, world.anton)
    entry = entry_of(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await manager_of(hass).runner.async_run(schedule.id)
    assert calls == []
    assert manager_of(hass).store.get(schedule.id) is not None  # not deleted as "unconfigured"

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await manager_of(hass).runner.async_run(schedule.id)
    assert len(calls) == 1


async def _unloaded_with_ui_schedule(hass: HomeAssistant, world: World) -> Schedule:
    """Give bob (a UI user) a schedule, then unload the config entry."""
    await make_ui_user(hass, world.bob)
    schedule = await create(hass, world.bob)
    assert await hass.config_entries.async_unload(entry_of(hass).entry_id)
    await hass.async_block_till_done()
    return schedule


async def test_a_user_update_while_unloaded_keeps_ui_schedules(
    hass: HomeAssistant, world: World
) -> None:
    schedule = await _unloaded_with_ui_schedule(hass, world)

    await hass.auth.async_update_user(world.bob, name="Bobby")
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(schedule.id) is not None


async def test_a_reload_while_unloaded_keeps_ui_schedules(
    hass: HomeAssistant, world: World
) -> None:
    schedule = await _unloaded_with_ui_schedule(hass, world)
    config = CONFIG_SCHEMA({"haac_bridge": {"users": []}})

    with patch(YAML_CONFIG, return_value=config):
        await async_reload(hass)
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(schedule.id) is not None


async def test_removing_another_user_while_unloaded_keeps_ui_schedules(
    hass: HomeAssistant, world: World, add_user: Callable[..., User]
) -> None:
    carol = add_user("carol")
    schedule = await _unloaded_with_ui_schedule(hass, world)

    await hass.auth.async_remove_user(carol)
    await hass.async_block_till_done()

    assert manager_of(hass).store.get(schedule.id) is not None


async def test_ui_schedules_survive_the_unload_and_run_again_after_setup(
    hass: HomeAssistant, world: World
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    schedule = await _unloaded_with_ui_schedule(hass, world)
    await hass.auth.async_update_user(world.bob, name="Bobby")
    await hass.async_block_till_done()

    assert await hass.config_entries.async_setup(entry_of(hass).entry_id)
    await hass.async_block_till_done()
    await manager_of(hass).runner.async_run(schedule.id)

    assert manager_of(hass).store.get(schedule.id) is not None
    assert len(calls) == 1


async def test_a_new_manager_waits_for_the_users(hass: HomeAssistant) -> None:
    manager = ScheduleManager(hass)
    stray = make_schedule(owner="nobody")
    await manager.store.async_add(stray)

    await manager.async_sweep()

    assert manager.users_ready is False
    assert manager.store.get(stray.id) is not None

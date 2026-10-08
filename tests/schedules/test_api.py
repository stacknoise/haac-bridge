"""Tests for the schedule commands: ownership, admins, validation and subscription (concept 19.4)."""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.haac_bridge.core.runtime import get_data

from .conftest import World

CLIENT = Callable[[User], Coroutine[Any, Any, Any]]
CREATE: dict[str, Any] = {
    "name": " Morning light ",
    "when": {"type": "time", "time": "06:45", "days": [0, 1, 2, 3, 4]},
    "action": "turn_on",
    "entities": ["switch.garage_socket"],
}
PREFIX = "haac_bridge/"


async def ws(client: Any, command: str, **fields: Any) -> dict[str, Any]:
    """Send a haac_bridge command and return its reply."""
    await client.send_json_auto_id({"type": PREFIX + command, **fields})
    return await client.receive_json()


async def create(client: Any, **changes: Any) -> dict[str, Any]:
    """Create a schedule and return the schedule from the reply; fail the test on an error."""
    reply = await ws(client, "schedules/create", **{**CREATE, **changes})
    assert reply["success"], reply
    return reply["result"]


def targets(call: ServiceCall) -> list[str]:
    """Return the target entities of a service call as a list."""
    entity_id = call.data["entity_id"]
    return [entity_id] if isinstance(entity_id, str) else list(entity_id)


def error_code(reply: dict[str, Any]) -> str:
    """Return the HAB code of an error reply."""
    assert not reply["success"], reply
    return reply["error"]["code"]


async def test_create_list_and_revision(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton)
    assert schedule["name"] == "Morning light"
    assert schedule["owner"] == world.anton.id
    assert schedule["owner_name"] == "Anton"
    assert schedule["own"] is True
    assert schedule["enabled"] is True
    assert schedule["next_run"] is not None
    assert schedule["paused"] is None
    assert schedule["last_run"] is None

    listing = (await ws(anton, "schedules/list"))["result"]
    assert listing["scope"] == "own"
    assert [item["id"] for item in listing["schedules"]] == [schedule["id"]]
    revision = (await ws(anton, "schedules/revision"))["result"]
    assert revision == {"revision": listing["revision"], "scope": "own"}


async def test_disabled_schedule_has_no_next_run(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton, enabled=False)
    assert schedule["enabled"] is False
    assert schedule["next_run"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"name": ""},
        {"when": {"type": "time", "time": "25:00", "days": [0]}},
        {"when": {"type": "sunrise", "days": []}},
        {"action": "dim"},
        {"entities": []},
        {"entities": ["light.kitchen"]},
        {"enabled": "yes"},
    ],
)
async def test_invalid_schedule_is_rejected(
    world: World, client_for: CLIENT, changes: dict[str, Any]
) -> None:
    anton = await client_for(world.anton)
    reply = await ws(anton, "schedules/create", **{**CREATE, **changes})
    assert error_code(reply) == "HAB-SCH-001"
    assert (await ws(anton, "schedules/list"))["result"]["schedules"] == []


async def test_missing_field_is_a_request_error(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    fields = {key: value for key, value in CREATE.items() if key != "name"}
    assert error_code(await ws(anton, "schedules/create", **fields)) == "HAB-WS-001"


async def test_entities_must_be_exposed_to_the_caller(world: World, client_for: CLIENT) -> None:
    lena = await client_for(world.lena)  # sees only switch.office_fan
    assert error_code(await ws(lena, "schedules/create", **CREATE)) == "HAB-SCH-001"
    assert (await create(lena, entities=["switch.office_fan"]))["owner"] == world.lena.id


async def test_a_user_who_is_not_configured_cannot_create(world: World, client_for: CLIENT) -> None:
    bob = await client_for(world.bob)
    assert error_code(await ws(bob, "schedules/create", **CREATE)) == "HAB-SCH-001"


async def test_limit_per_user(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    with patch("custom_components.haac_bridge.schedules.manager.MAX_SCHEDULES_PER_USER", 1):
        await create(anton)
        assert error_code(await ws(anton, "schedules/create", **CREATE)) == "HAB-SCH-005"
        lena = await client_for(world.lena)
        await create(lena, entities=["switch.office_fan"])  # the limit is per user


async def test_update_changes_the_schedule(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton)
    reply = await ws(
        anton,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        name="Evening light",
        action="turn_off",
        enabled=False,
        when={"type": "sunset", "days": [5, 6], "offset_min": -30},
        entities=["switch.garage_socket", "switch.office_fan"],
    )
    assert reply["success"], reply
    result = reply["result"]
    assert result["name"] == "Evening light"
    assert result["action"] == "turn_off"
    assert result["enabled"] is False
    assert result["when"] == {"type": "sunset", "days": [5, 6], "offset_min": -30}
    assert result["entities"] == ["switch.garage_socket", "switch.office_fan"]
    assert result["next_run"] is None
    assert result["updated_at"] != schedule["updated_at"]
    assert result["created_at"] == schedule["created_at"]


async def test_update_with_an_old_version_conflicts(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton)
    first = await ws(
        anton,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        name="One",
    )
    assert first["success"]
    stale = await ws(
        anton,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        name="Two",
    )
    assert error_code(stale) == "HAB-SCH-004"
    listing = (await ws(anton, "schedules/list"))["result"]
    assert listing["schedules"][0]["name"] == "One"


async def test_update_of_an_unknown_schedule(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    reply = await ws(
        anton,
        "schedules/update",
        schedule_id="nope",
        updated_at="2026-10-01T05:12:00+00:00",
        name="X",
    )
    assert error_code(reply) == "HAB-SCH-003"


async def test_update_with_invalid_values(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    schedule = await create(anton)
    base = {"schedule_id": schedule["id"], "updated_at": schedule["updated_at"]}
    assert error_code(await ws(anton, "schedules/update", **base, name=" ")) == "HAB-SCH-001"
    assert error_code(await ws(anton, "schedules/update", **base, enabled=1)) == "HAB-SCH-001"
    lena = await client_for(world.lena)
    own = await create(lena, entities=["switch.office_fan"])
    reply = await ws(
        lena,
        "schedules/update",
        schedule_id=own["id"],
        updated_at=own["updated_at"],
        entities=["switch.garage_socket"],
    )
    assert error_code(reply) == "HAB-SCH-001"


async def test_regular_users_cannot_touch_foreign_schedules(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    lena = await client_for(world.lena)
    schedule = await create(anton)
    update = await ws(
        lena,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        name="Mine now",
    )
    assert error_code(update) == "HAB-SCH-006"
    assert (
        error_code(await ws(lena, "schedules/delete", schedule_id=schedule["id"])) == "HAB-SCH-006"
    )
    assert (
        error_code(await ws(lena, "schedules/run_now", schedule_id=schedule["id"])) == "HAB-SCH-006"
    )
    assert (await ws(lena, "schedules/list"))["result"]["schedules"] == []
    assert len((await ws(anton, "schedules/list"))["result"]["schedules"]) == 1


async def test_admins_see_all_and_change_all_but_entities(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    lena = await client_for(world.lena)
    root = await client_for(world.root)
    mine = await create(anton)
    hers = await create(lena, entities=["switch.office_fan"])

    listing = (await ws(root, "schedules/list"))["result"]
    assert listing["scope"] == "all"
    assert {item["id"]: item["owner_name"] for item in listing["schedules"]} == {
        mine["id"]: "Anton",
        hers["id"]: "Lena",
    }
    assert {item["id"]: item["own"] for item in listing["schedules"]} == {
        mine["id"]: False,
        hers["id"]: False,
    }
    assert (await ws(root, "schedules/revision"))["result"]["scope"] == "all"

    base = {"schedule_id": mine["id"], "updated_at": mine["updated_at"]}
    renamed = await ws(root, "schedules/update", **base, name="Renamed", enabled=False)
    assert renamed["success"], renamed
    assert renamed["result"]["name"] == "Renamed"
    assert renamed["result"]["owner"] == world.anton.id

    base["updated_at"] = renamed["result"]["updated_at"]
    other_entities = await ws(root, "schedules/update", **base, entities=["switch.office_fan"])
    assert error_code(other_entities) == "HAB-SCH-006"
    same_entities = await ws(root, "schedules/update", **base, entities=mine["entities"])
    assert same_entities["success"], same_entities


async def test_admin_creates_for_themselves(world: World, client_for: CLIENT) -> None:
    root = await client_for(world.root)
    assert (await create(root))["owner"] == world.root.id


async def test_delete_is_idempotent_and_admins_may_delete_foreign(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    root = await client_for(world.root)
    schedule = await create(anton)
    assert (await ws(anton, "schedules/delete", schedule_id="unknown"))["success"]
    assert (await ws(root, "schedules/delete", schedule_id=schedule["id"]))["success"]
    assert (await ws(anton, "schedules/delete", schedule_id=schedule["id"]))["success"]
    assert (await ws(anton, "schedules/list"))["result"]["schedules"] == []


@pytest.fixture
def no_cooldown() -> Any:
    """Allow run_now of the same schedule again at once."""
    with patch("custom_components.haac_bridge.schedules.manager.RUN_NOW_COOLDOWN", 0):
        yield


@pytest.mark.usefixtures("no_cooldown")
async def test_run_now_switches_as_the_owner(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    anton = await client_for(world.anton)
    root = await client_for(world.root)
    schedule = await create(anton, entities=["switch.garage_socket", "switch.office_fan"])

    assert (await ws(anton, "schedules/run_now", schedule_id=schedule["id"]))["success"]
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(calls) == 2
    assert {call.context.user_id for call in calls} == {world.anton.id}
    assert [targets(call) for call in calls] == [["switch.garage_socket"], ["switch.office_fan"]]

    assert (await ws(root, "schedules/run_now", schedule_id=schedule["id"]))["success"]
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(calls) == 4
    assert {call.context.user_id for call in calls} == {world.anton.id}

    last_run = (await ws(anton, "schedules/list"))["result"]["schedules"][0]["last_run"]
    assert last_run["result"] == "ok"
    assert last_run["code"] is None


async def test_run_now_of_an_unknown_schedule(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    assert error_code(await ws(anton, "schedules/run_now", schedule_id="nope")) == "HAB-SCH-003"


async def test_subscription_reports_only_the_callers_changes(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    lena = await client_for(world.lena)

    subscribed = await ws(lena, "subscribe_schedules")
    assert subscribed["success"]
    assert subscribed["result"] is None
    subscription_id = subscribed["id"]

    await create(anton)  # not visible to lena: no event for her

    await lena.send_json_auto_id(
        {"type": PREFIX + "schedules/create", **CREATE, "entities": ["switch.office_fan"]}
    )
    messages = [await lena.receive_json(), await lena.receive_json()]
    events = [message for message in messages if message["type"] == "event"]
    assert len(events) == 1
    assert events[0]["id"] == subscription_id
    revision = get_data(hass).schedules.revision_for(world.lena)
    assert events[0]["event"] == {"schedules_changed": {"revision": revision}}


async def test_bridge_entities_are_never_exposed_nor_schedulable(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "switch", "haac_bridge", "schedule_x_enabled", suggested_object_id="hidden"
    )
    hass.states.async_set("switch.hidden", "on")
    anton = await client_for(world.anton)

    entities = (await ws(anton, "entities/list"))["result"]["entities"]
    ids = [entity["entity_id"] for entity in entities]
    assert "switch.hidden" not in ids
    assert "switch.garage_socket" in ids

    reply = await ws(anton, "schedules/create", **{**CREATE, "entities": ["switch.hidden"]})
    assert error_code(reply) == "HAB-SCH-001"
    call = await ws(
        anton, "call_service", entity_id="switch.hidden", service="turn_off", service_data={}
    )
    assert error_code(call) == "HAB-SVC-001"


async def test_run_now_answers_before_the_run_ends(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    release = asyncio.Event()

    async def _slow(call: ServiceCall) -> None:
        await release.wait()

    hass.services.async_register("switch", "turn_on", _slow)
    anton = await client_for(world.anton)
    schedule = await create(anton)

    reply = await asyncio.wait_for(ws(anton, "schedules/run_now", schedule_id=schedule["id"]), 5)
    assert reply["success"]
    assert (await ws(anton, "schedules/list"))["result"]["schedules"][0]["last_run"] is None

    release.set()
    await hass.async_block_till_done(wait_background_tasks=True)
    last_run = (await ws(anton, "schedules/list"))["result"]["schedules"][0]["last_run"]
    assert last_run["result"] == "ok"


async def test_run_now_again_within_the_cooldown_is_refused(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    calls = async_mock_service(hass, "switch", "turn_on")
    anton = await client_for(world.anton)
    schedule = await create(anton)

    assert (await ws(anton, "schedules/run_now", schedule_id=schedule["id"]))["success"]
    await hass.async_block_till_done(wait_background_tasks=True)
    reply = await ws(anton, "schedules/run_now", schedule_id=schedule["id"])

    assert error_code(reply) == "HAB-SCH-007"
    assert len(calls) == 1


@pytest.mark.usefixtures("no_cooldown")
async def test_run_now_while_the_schedule_runs_is_refused(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    release = asyncio.Event()

    async def _slow(call: ServiceCall) -> None:
        await release.wait()

    hass.services.async_register("switch", "turn_on", _slow)
    anton = await client_for(world.anton)
    schedule = await create(anton)

    assert (await ws(anton, "schedules/run_now", schedule_id=schedule["id"]))["success"]
    assert error_code(await ws(anton, "schedules/run_now", schedule_id=schedule["id"])) == (
        "HAB-SCH-007"
    )
    release.set()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert (await ws(anton, "schedules/run_now", schedule_id=schedule["id"]))["success"]
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_a_second_schedule_subscription_replaces_the_first(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    first = await ws(anton, "subscribe_schedules")
    second = await ws(anton, "subscribe_schedules")
    assert first["success"]
    assert second["success"]

    await anton.send_json_auto_id({"type": PREFIX + "schedules/create", **CREATE})
    messages = [await anton.receive_json(), await anton.receive_json()]
    events = [message for message in messages if message["type"] == "event"]
    assert [event["id"] for event in events] == [second["id"]]

"""Tests for the run log and its command (concept 19.11)."""

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import Unauthorized
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.haac_bridge.core.runtime import get_data
from custom_components.haac_bridge.schedules.model import RunEntry, RunResult, RunTrigger
from custom_components.haac_bridge.schedules.run_log import ScheduleRunLog

from .conftest import World
from .test_api import CREATE, create as create_schedule, ws

KEY = "haac_bridge.schedule_runs"
CLIENT = Callable[[User], Coroutine[Any, Any, Any]]


def entry(
    owner: str = "user-1", *, at: datetime | None = None, result: RunResult = RunResult.OK
) -> RunEntry:
    """Return a run of a schedule of `owner`, now unless `at` is given."""
    return RunEntry(
        schedule_id="schedule-1",
        owner=owner,
        name="Morning light",
        at=at or dt_util.utcnow(),
        result=result,
        code=None,
        trigger=RunTrigger.PLAN,
        removed=False,
        notify=True,
    )


async def loaded(hass: HomeAssistant) -> ScheduleRunLog:
    """Return a loaded run log."""
    log = ScheduleRunLog(hass)
    await log.async_load()
    return log


async def test_entries_are_numbered_and_filtered_by_owner(hass: HomeAssistant) -> None:
    log = await loaded(hass)
    log.record(entry("anton"))
    log.record(entry("lena"))
    log.record(entry("anton", result=RunResult.FAILED))

    assert log.last_seq == 3
    assert [run["seq"] for run in log.runs_of("anton")] == [1, 3]
    assert [run["seq"] for run in log.runs_of("anton", after_seq=1)] == [3]
    assert log.runs_of("anton", after_seq=3) == []
    assert log.last_seq_of("lena") == 2
    assert log.last_seq_of("nobody") == 0
    assert log.owners() == {"anton", "lena"}


async def test_an_entry_carries_every_field(hass: HomeAssistant) -> None:
    log = await loaded(hass)
    at = datetime(2026, 10, 19, 6, 45, tzinfo=UTC)
    log.record(entry(at=at, result=RunResult.MISSED))
    assert log.runs_of("user-1") == [
        {
            "seq": 1,
            "schedule_id": "schedule-1",
            "owner": "user-1",
            "name": "Morning light",
            "at": at.isoformat(),
            "result": "missed",
            "code": None,
            "trigger": "plan",
            "removed": False,
            "notify": True,
        }
    ]


async def test_the_log_is_written_after_a_short_delay_and_read_again(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    log = await loaded(hass)
    log.record(entry())
    log.record(entry())
    assert KEY not in hass_storage
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
    await hass.async_block_till_done()
    assert hass_storage[KEY]["data"]["log_id"] == log.log_id

    again = await loaded(hass)
    assert again.log_id == log.log_id
    assert again.last_seq == 2
    assert again.runs_of("user-1") == log.runs_of("user-1")


async def test_an_empty_store_gets_a_new_log_id(hass: HomeAssistant) -> None:
    assert (await loaded(hass)).log_id != (await loaded(hass)).log_id


async def test_numbers_keep_counting_after_old_entries_are_gone(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    hass_storage[KEY] = {
        "version": 1,
        "key": KEY,
        "data": {"log_id": "log-a", "seq": 9, "entries": []},
    }
    log = await loaded(hass)
    log.record(entry())
    assert log.log_id == "log-a"
    assert [run["seq"] for run in log.runs_of("user-1")] == [10]


async def test_damaged_entries_are_dropped(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    good = ScheduleRunLog(hass)
    good.record(entry())
    stored = good.runs_of("user-1")[0]
    hass_storage[KEY] = {
        "version": 1,
        "key": KEY,
        "data": {"log_id": "log-a", "seq": 1, "entries": [stored, {"seq": 2}, "text"]},
    }
    log = await loaded(hass)
    assert [run["seq"] for run in log.runs_of("user-1")] == [1]


async def test_entries_older_than_the_retention_go(hass: HomeAssistant) -> None:
    log = await loaded(hass)
    log.record(entry(at=dt_util.utcnow() - timedelta(days=31)))
    log.record(entry(at=dt_util.utcnow() - timedelta(days=29)))
    assert [run["seq"] for run in log.runs_of("user-1")] == [2]


async def test_the_oldest_entries_of_an_owner_go_above_the_limit(hass: HomeAssistant) -> None:
    log = await loaded(hass)
    with patch("custom_components.haac_bridge.schedules.run_log.MAX_RUN_LOG_PER_OWNER", 2):
        for _ in range(3):
            log.record(entry("anton"))
        log.record(entry("lena"))
    assert [run["seq"] for run in log.runs_of("anton")] == [2, 3]
    assert [run["seq"] for run in log.runs_of("lena")] == [4]


async def test_remove_owners_keeps_the_others(hass: HomeAssistant) -> None:
    log = await loaded(hass)
    log.record(entry("anton"))
    log.record(entry("lena"))
    assert log.remove_owners({"anton"})
    assert not log.remove_owners({"anton"})
    assert log.owners() == {"lena"}
    assert log.last_seq == 2


async def test_a_run_writes_an_entry_with_every_result(hass: HomeAssistant, world: World) -> None:
    async_mock_service(hass, "switch", "turn_on")
    manager = get_data(hass).schedules
    schedule = await manager.async_create(world.anton, {**CREATE, "notify": True})
    await manager.runner.async_run(schedule.id)
    await manager.runner.async_run(schedule.id, world.anton.id)

    first, second = manager.run_log.runs_of(world.anton.id)
    assert (first["result"], first["trigger"], first["code"]) == ("ok", "plan", None)
    assert (second["trigger"], second["notify"], second["name"]) == (
        "manual",
        True,
        "Morning light",
    )
    assert first["schedule_id"] == schedule.id
    assert first["removed"] is False


async def test_a_failed_run_is_logged_with_its_code(hass: HomeAssistant, world: World) -> None:
    manager = get_data(hass).schedules
    schedule = await manager.async_create(world.anton, CREATE)

    async def _refuse(call: ServiceCall) -> None:
        raise Unauthorized(context=call.context)

    hass.services.async_register("switch", "turn_on", _refuse)
    await manager.runner.async_run(schedule.id)
    (run,) = manager.run_log.runs_of(world.anton.id)
    assert (run["result"], run["code"], run["notify"]) == ("failed", "HAB-SCH-002", False)


async def test_a_run_without_exposed_entities_is_logged_as_failed(
    hass: HomeAssistant, world: World
) -> None:
    manager = get_data(hass).schedules
    schedule = await manager.async_create(world.anton, CREATE)
    with patch.object(get_data(hass).exposure, "is_exposed", return_value=False):
        await manager.runner.async_run(schedule.id)
    (run,) = manager.run_log.runs_of(world.anton.id)
    assert (run["result"], run["code"]) == ("failed", "HAB-SCH-002")


async def test_a_run_dropped_after_the_reload_is_logged_as_missed(
    hass: HomeAssistant, world: World
) -> None:
    manager = get_data(hass).schedules
    schedule = await manager.async_create(world.anton, CREATE)
    manager.users_ready = False
    await manager.runner.async_run(schedule.id)
    manager.users_ready = True
    with patch("custom_components.haac_bridge.schedules.runner.MISSED_RUN_GRACE", timedelta(0)):
        manager.runner.async_run_deferred()
    (run,) = manager.run_log.runs_of(world.anton.id)
    assert (run["result"], run["code"], run["trigger"]) == ("missed", None, "plan")


async def test_runs_returns_only_own_entries_after_the_cursor(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    async_mock_service(hass, "switch", "turn_on")
    anton = await client_for(world.anton)
    root = await client_for(world.root)
    mine = await create_schedule(anton)
    hers = await create_schedule(root)
    manager = get_data(hass).schedules
    await manager.runner.async_run(mine["id"])
    await manager.runner.async_run(hers["id"])
    await manager.runner.async_run(mine["id"])

    reply = (await ws(anton, "schedules/runs"))["result"]
    assert reply["log_id"] == manager.run_log.log_id
    assert reply["last_seq"] == 3
    assert [run["seq"] for run in reply["runs"]] == [1, 3]

    later = (await ws(anton, "schedules/runs", log_id=reply["log_id"], after_seq=1))["result"]
    assert [run["seq"] for run in later["runs"]] == [3]

    # An admin sees only their own runs, not those of the schedules they can list.
    admin = (await ws(root, "schedules/runs"))["result"]
    assert [run["seq"] for run in admin["runs"]] == [2]


async def test_a_different_log_id_returns_everything(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    async_mock_service(hass, "switch", "turn_on")
    anton = await client_for(world.anton)
    schedule = await create_schedule(anton)
    await get_data(hass).schedules.runner.async_run(schedule["id"])

    reply = (await ws(anton, "schedules/runs", log_id="older-log", after_seq=1))["result"]
    assert [run["seq"] for run in reply["runs"]] == [1]


async def test_runs_rejects_a_negative_cursor(world: World, client_for: CLIENT) -> None:
    anton = await client_for(world.anton)
    reply = await ws(anton, "schedules/runs", after_seq=-1)
    assert reply["error"]["code"] == "HAB-WS-001"


async def test_revision_follows_notify_and_new_runs(
    hass: HomeAssistant, world: World, client_for: CLIENT
) -> None:
    async_mock_service(hass, "switch", "turn_on")
    anton = await client_for(world.anton)
    lena = await client_for(world.lena)
    schedule = await create_schedule(anton)

    async def revision(client: Any) -> str:
        return (await ws(client, "schedules/revision"))["result"]["revision"]

    before = await revision(anton)
    other = await revision(lena)
    await ws(
        anton,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=schedule["updated_at"],
        notify=True,
    )
    after_notify = await revision(anton)
    assert after_notify != before

    await get_data(hass).schedules.runner.async_run(schedule["id"])
    assert await revision(anton) != after_notify
    assert await revision(lena) == other


async def test_notify_is_off_by_default_and_only_the_owner_changes_it(
    world: World, client_for: CLIENT
) -> None:
    anton = await client_for(world.anton)
    root = await client_for(world.root)
    schedule = await create_schedule(anton)
    assert schedule["notify"] is False

    base = {"schedule_id": schedule["id"], "updated_at": schedule["updated_at"]}
    denied = await ws(root, "schedules/update", **base, notify=True)
    assert denied["error"]["code"] == "HAB-SCH-006"
    bad = await ws(anton, "schedules/update", **base, notify="yes")
    assert bad["error"]["code"] == "HAB-SCH-001"
    changed = await ws(anton, "schedules/update", **base, notify=True)
    assert changed["result"]["notify"] is True
    # An admin may send the unchanged value along with other edits.
    same = await ws(
        root,
        "schedules/update",
        schedule_id=schedule["id"],
        updated_at=changed["result"]["updated_at"],
        notify=True,
        name="Renamed",
    )
    assert same["result"]["name"] == "Renamed"


async def test_deleting_a_ha_user_clears_their_entries(hass: HomeAssistant, world: World) -> None:
    manager = get_data(hass).schedules
    manager.run_log.record(entry(world.anton.id))
    manager.run_log.record(entry(world.lena.id))
    await hass.auth.async_remove_user(world.anton)
    await hass.async_block_till_done()
    assert manager.run_log.owners() == {world.lena.id}


async def test_the_sweep_clears_entries_of_users_who_are_not_configured(
    hass: HomeAssistant, world: World
) -> None:
    manager = get_data(hass).schedules
    manager.run_log.record(entry(world.bob.id))
    manager.run_log.record(entry(world.lena.id))
    await manager.async_sweep(world.lena.id)
    assert manager.run_log.owners() == {world.bob.id, world.lena.id}
    await manager.async_sweep()
    assert manager.run_log.owners() == {world.lena.id}

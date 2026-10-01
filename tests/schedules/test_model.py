"""Tests for schedule validation and (de)serialisation (concept 19.2)."""

from datetime import UTC, datetime, time
from typing import Any

import pytest

from custom_components.haac_bridge.core.errors import ErrorCode, ScheduleError
from custom_components.haac_bridge.schedules.model import (
    Action,
    LastRun,
    Paused,
    PauseReason,
    RunResult,
    WhenType,
    new_schedule,
    parse_entities,
    parse_name,
    parse_when,
    schedule_from_dict,
)

NOW = datetime(2026, 10, 1, 5, 12, tzinfo=UTC)
FIELDS: dict[str, Any] = {
    "name": "  Morning light ",
    "when": {"type": "time", "time": "06:45", "days": [0, 1, 2, 3, 4]},
    "action": "turn_on",
    "entities": ["switch.garage_socket", "switch.office_fan"],
}


def test_new_schedule_normalises_and_defaults() -> None:
    schedule = new_schedule("user-1", FIELDS, NOW)
    assert schedule.name == "Morning light"
    assert schedule.enabled is True
    assert schedule.when.type is WhenType.TIME
    assert schedule.when.time == time(6, 45)
    assert schedule.when.days == frozenset({0, 1, 2, 3, 4})
    assert schedule.action is Action.TURN_ON
    assert schedule.entities == ("switch.garage_socket", "switch.office_fan")
    assert schedule.created_at == schedule.updated_at == NOW
    assert schedule.paused is None
    assert schedule.last_run is None
    assert schedule.active


def test_new_schedule_ids_are_unique() -> None:
    assert new_schedule("u", FIELDS).id != new_schedule("u", FIELDS).id


def test_sun_trigger_with_offset() -> None:
    when = parse_when({"type": "sunset", "days": [5, 6], "offset_min": -30})
    assert when.type is WhenType.SUNSET
    assert when.offset_min == -30
    assert when.time is None
    assert when.to_dict() == {"type": "sunset", "days": [5, 6], "offset_min": -30}


def test_sun_trigger_offset_defaults_to_zero() -> None:
    assert parse_when({"type": "sunrise", "days": [0]}).offset_min == 0


@pytest.mark.parametrize(
    "when",
    [
        None,
        {},
        {"type": "weekly", "days": [0], "time": "06:00"},
        {"type": "time", "days": [0]},
        {"type": "time", "days": [0], "time": "6:45"},
        {"type": "time", "days": [0], "time": "24:00"},
        {"type": "time", "days": [0], "time": "06:60"},
        {"type": "time", "days": [0], "time": "06:45:00"},
        {"type": "time", "days": [0], "time": 645},
        {"type": "time", "days": [], "time": "06:45"},
        {"type": "time", "time": "06:45"},
        {"type": "time", "days": [7], "time": "06:45"},
        {"type": "time", "days": [-1], "time": "06:45"},
        {"type": "time", "days": [True], "time": "06:45"},
        {"type": "time", "days": ["0"], "time": "06:45"},
        {"type": "time", "days": [0], "time": "06:45", "offset_min": 5},
        {"type": "sunrise", "days": [0], "time": "06:45"},
        {"type": "sunrise", "days": [0], "offset_min": 181},
        {"type": "sunrise", "days": [0], "offset_min": -181},
        {"type": "sunrise", "days": [0], "offset_min": 1.5},
        {"type": "sunrise", "days": [0], "offset_min": True},
    ],
)
def test_invalid_when(when: object) -> None:
    with pytest.raises(ScheduleError) as error:
        parse_when(when)
    assert error.value.code is ErrorCode.SCH_INVALID


def test_offset_limits_are_inclusive() -> None:
    assert parse_when({"type": "sunrise", "days": [0], "offset_min": 180}).offset_min == 180
    assert parse_when({"type": "sunrise", "days": [0], "offset_min": -180}).offset_min == -180


@pytest.mark.parametrize("name", [None, 5, "", "   ", "x" * 61])
def test_invalid_name(name: object) -> None:
    with pytest.raises(ScheduleError):
        parse_name(name)


def test_name_limits_are_inclusive() -> None:
    assert parse_name("x") == "x"
    assert parse_name("x" * 60) == "x" * 60


@pytest.mark.parametrize(
    "entities",
    [
        None,
        "switch.garage_socket",
        [],
        ["light.kitchen"],
        ["sensor.bath_humidity"],
        ["switch"],
        ["Switch.Garage"],
        [5],
        [f"switch.a{i}" for i in range(21)],
    ],
)
def test_invalid_entities(entities: object) -> None:
    with pytest.raises(ScheduleError):
        parse_entities(entities)


def test_entities_are_deduplicated_in_order() -> None:
    entities = ["switch.b", "switch.a", "switch.b"]
    assert parse_entities(entities) == ("switch.b", "switch.a")
    assert len(parse_entities([f"switch.a{i}" for i in range(20)])) == 20


@pytest.mark.parametrize(
    ("key", "value"),
    [("action", "dim"), ("action", None), ("enabled", "yes"), ("enabled", 1)],
)
def test_invalid_top_level_fields(key: str, value: object) -> None:
    with pytest.raises(ScheduleError):
        new_schedule("u", {**FIELDS, key: value})


def test_missing_fields_are_invalid() -> None:
    for key in ("name", "when", "action", "entities"):
        fields = {k: v for k, v in FIELDS.items() if k != key}
        with pytest.raises(ScheduleError):
            new_schedule("u", fields)


def test_round_trip_with_pause_and_last_run() -> None:
    schedule = new_schedule("user-1", FIELDS, NOW).with_changes(
        paused=Paused(PauseReason.NO_ENTITIES, NOW),
        last_run=LastRun(NOW, RunResult.PARTIAL, "HAB-SCH-002"),
    )
    restored = schedule_from_dict(schedule.to_dict())
    assert restored == schedule
    assert not restored.active


def test_disabled_schedule_is_not_active() -> None:
    assert not new_schedule("u", {**FIELDS, "enabled": False}).active


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("owner"),
        lambda d: d.update(id=5),
        lambda d: d.update(enabled="yes"),
        lambda d: d.update(created_at="yesterday"),
        lambda d: d.update(updated_at=None),
        lambda d: d.update(paused={"reason": "bored", "at": "2026-10-01T05:12:00+00:00"}),
        lambda d: d.update(last_run={"at": "2026-10-01T05:12:00+00:00", "result": "great"}),
        lambda d: d.update(last_run={"at": "2026-10-01T05:12:00+00:00", "result": "ok", "code": 5}),
        lambda d: d.update(entities=[]),
    ],
)
def test_damaged_stored_schedule_is_rejected(mutate: Any) -> None:
    data = new_schedule("u", FIELDS, NOW).to_dict()
    mutate(data)
    with pytest.raises(ScheduleError):
        schedule_from_dict(data)


def test_stored_form_matches_the_concept() -> None:
    data = new_schedule("user-1", FIELDS, NOW).to_dict()
    assert data["when"] == {"type": "time", "time": "06:45", "days": [0, 1, 2, 3, 4]}
    assert data["action"] == "turn_on"
    assert data["paused"] is None
    assert data["last_run"] is None
    assert data["created_at"] == "2026-10-01T05:12:00+00:00"

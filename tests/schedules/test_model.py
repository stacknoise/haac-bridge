"""Tests for schedule validation and (de)serialisation (concept 19.2)."""

from datetime import UTC, date, datetime, time
from typing import Any

import pytest

from custom_components.haac_bridge.core.errors import ErrorCode, ScheduleError
from custom_components.haac_bridge.schedules.model import (
    Action,
    LastRun,
    OffReason,
    Paused,
    PauseReason,
    Repeat,
    RepeatFreq,
    RunEntry,
    RunResult,
    RunTrigger,
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


MONDAY = datetime(2026, 10, 19, 8, 0, tzinfo=UTC)


def _fields(**extra: Any) -> dict[str, Any]:
    return {**FIELDS, **extra}


def test_extension_fields_default_for_old_schedules() -> None:
    schedule = new_schedule("u", FIELDS, NOW)
    assert schedule.repeat == Repeat(RepeatFreq.WEEKLY, 1)
    assert schedule.notify is False
    assert schedule.off_reason is None
    legacy = schedule.to_dict()
    for key in ("repeat", "notify", "off_reason"):
        del legacy[key]
    assert schedule_from_dict(legacy).repeat == Repeat()


def test_extension_fields_round_trip() -> None:
    fields = _fields(
        notify=True,
        repeat={
            "freq": "weekly",
            "interval": 2,
            "start_date": "2026-10-19",
            "end_date": "2026-12-31",
        },
    )
    schedule = new_schedule("u", fields, MONDAY).with_changes(off_reason=OffReason.ENTITY_DISABLED)
    stored = schedule.to_dict()
    assert stored["repeat"] == fields["repeat"]
    assert stored["off_reason"] == "entity_disabled"
    assert schedule_from_dict(stored) == schedule


def test_repeat_start_date_defaults_to_today() -> None:
    schedule = new_schedule("u", _fields(repeat={"freq": "daily", "interval": 3}), MONDAY)
    assert schedule.repeat.start_date == date(2026, 10, 19)


def test_non_weekly_repeat_needs_no_weekdays_and_round_trips() -> None:
    when = {"type": "time", "time": "07:00"}
    fields = _fields(when=when, repeat={"freq": "monthly", "start_date": "2026-10-19"})
    schedule = new_schedule("u", fields, MONDAY)
    assert schedule.when.days == frozenset()
    assert "days" not in schedule.when.to_dict()
    assert schedule_from_dict(schedule.to_dict()) == schedule


def test_weekly_repeat_needs_weekdays() -> None:
    fields = _fields(when={"type": "time", "time": "07:00"}, repeat={"freq": "weekly"})
    with pytest.raises(ScheduleError) as error:
        new_schedule("u", fields, MONDAY)
    assert error.value.code is ErrorCode.SCH_INVALID


@pytest.mark.parametrize(
    "repeat",
    [
        {"freq": "hourly"},
        {"freq": "daily", "interval": 0},
        {"freq": "daily", "interval": 366},
        {"freq": "weekly", "interval": 53},
        {"freq": "monthly", "interval": 13},
        {"freq": "yearly", "interval": 2},
        {"freq": "daily", "interval": True},
        {"freq": "once"},
        {"freq": "once", "start_date": "2026-10-26", "interval": 1},
        {"freq": "once", "start_date": "2026-10-26", "end_date": "2026-10-27"},
        {"freq": "once", "start_date": "26.10.2026"},
        {"freq": "daily", "start_date": "2026-10-20", "end_date": "2026-10-19"},
        {"freq": "daily", "start_date": "2026-10-19", "end_date": "2027-10-21"},
        {"freq": "once", "start_date": "2027-10-21"},
        {"freq": "daily", "other": 1},
        "daily",
    ],
)
def test_invalid_repeat_is_sch_001(repeat: Any) -> None:
    with pytest.raises(ScheduleError) as error:
        new_schedule("u", _fields(repeat=repeat), MONDAY)
    assert error.value.code is ErrorCode.SCH_INVALID


@pytest.mark.parametrize(
    "repeat",
    [
        {"freq": "once", "start_date": "2026-10-18"},
        {"freq": "once", "start_date": "2026-10-19"},
        {"freq": "daily", "start_date": "2026-10-01", "end_date": "2026-10-18"},
    ],
)
def test_past_dates_are_sch_009(repeat: dict[str, Any]) -> None:
    # "now" is 08:00 UTC; 00:01 on the same day is past in the test time zone as well
    when = {"type": "time", "time": "00:01", "days": [0]}
    with pytest.raises(ScheduleError) as error:
        new_schedule("u", _fields(when=when, repeat=repeat), MONDAY)
    assert error.value.code is ErrorCode.SCH_IN_PAST


def test_one_off_later_today_is_valid() -> None:
    when = {"type": "time", "time": "23:30"}
    repeat = {"freq": "once", "start_date": "2026-10-19"}
    schedule = new_schedule("u", _fields(when=when, repeat=repeat), MONDAY)
    assert schedule.repeat.freq is RepeatFreq.ONCE
    assert "interval" not in schedule.repeat.to_dict()


def test_one_off_in_366_days_and_end_date_after_a_year_are_valid() -> None:
    far = {"freq": "once", "start_date": "2027-10-20"}
    assert new_schedule("u", _fields(repeat=far), MONDAY).repeat.start_date == date(2027, 10, 20)
    long = {"freq": "yearly", "start_date": "2026-10-19", "end_date": "2027-10-20"}
    assert new_schedule("u", _fields(repeat=long), MONDAY).repeat.end_date == date(2027, 10, 20)


def test_notify_must_be_boolean() -> None:
    with pytest.raises(ScheduleError):
        new_schedule("u", _fields(notify="yes"), NOW)


def test_unknown_off_reason_is_rejected() -> None:
    stored = new_schedule("u", FIELDS, NOW).to_dict()
    stored["off_reason"] = "bored"
    with pytest.raises(ScheduleError):
        schedule_from_dict(stored)


def test_run_entry_and_missed_result() -> None:
    entry = RunEntry("s", "u", "Name", NOW, RunResult.MISSED, None, RunTrigger.PLAN, True, False)
    assert entry.result.value == "missed"

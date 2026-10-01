"""Schedule data model, validation and (de)serialisation (concept 19.2)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, time
from enum import StrEnum
from typing import Any, TypeVar
import uuid

from homeassistant.core import split_entity_id, valid_entity_id
from homeassistant.util import dt as dt_util

from ..const import (
    MAX_ENTITIES_PER_SCHEDULE,
    MAX_NAME_LENGTH,
    MAX_OFFSET_MIN,
    SCHEDULE_DOMAIN,
)
from ..core.errors import ErrorCode, ScheduleError

DAYS: frozenset[int] = frozenset(range(7))
"""All weekdays, 0 = Monday."""

_E = TypeVar("_E", bound=StrEnum)


class WhenType(StrEnum):
    """What triggers a schedule."""

    TIME = "time"
    SUNRISE = "sunrise"
    SUNSET = "sunset"


class Action(StrEnum):
    """What a schedule does with its entities."""

    TURN_ON = "turn_on"
    TURN_OFF = "turn_off"
    TOGGLE = "toggle"


class PauseReason(StrEnum):
    """Why the system paused a schedule (concept 19.6)."""

    OWNER_INACTIVE = "owner_inactive"
    NO_ENTITIES = "no_entities"
    SUN_UNAVAILABLE = "sun_unavailable"


class RunResult(StrEnum):
    """Outcome of the last run."""

    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class When:
    """When a schedule runs: a wall-clock time or a sun event, on some weekdays."""

    type: WhenType
    days: frozenset[int]
    time: time | None = None
    offset_min: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return the stored form; `time` only for fixed times, `offset_min` only for sun events."""
        data: dict[str, Any] = {"type": self.type.value, "days": sorted(self.days)}
        if self.type is WhenType.TIME and self.time is not None:
            data["time"] = self.time.strftime("%H:%M")
        else:
            data["offset_min"] = self.offset_min
        return data


@dataclass(frozen=True, slots=True)
class Paused:
    """A pause set by the system, with its reason and the time it started."""

    reason: PauseReason
    at: datetime


@dataclass(frozen=True, slots=True)
class LastRun:
    """The outcome of the last run: when, the result and the HAB code if it was not ok."""

    at: datetime
    result: RunResult
    code: str | None = None


@dataclass(frozen=True, slots=True)
class Schedule:
    """One schedule as stored by the bridge."""

    id: str
    owner: str
    name: str
    enabled: bool
    when: When
    action: Action
    entities: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    paused: Paused | None = None
    last_run: LastRun | None = None

    @property
    def active(self) -> bool:
        """Return whether the schedule is planned: enabled and not paused by the system."""
        return self.enabled and self.paused is None

    def to_dict(self) -> dict[str, Any]:
        """Return the stored (JSON) form."""
        return {
            "id": self.id,
            "owner": self.owner,
            "name": self.name,
            "enabled": self.enabled,
            "when": self.when.to_dict(),
            "action": self.action.value,
            "entities": list(self.entities),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "paused": None
            if self.paused is None
            else {"reason": self.paused.reason.value, "at": self.paused.at.isoformat()},
            "last_run": None
            if self.last_run is None
            else {
                "at": self.last_run.at.isoformat(),
                "result": self.last_run.result.value,
                "code": self.last_run.code,
            },
        }

    def with_changes(self, **changes: Any) -> Schedule:
        """Return a copy with the given fields replaced."""
        return replace(self, **changes)


def _invalid() -> ScheduleError:
    """Return the error for a schedule that failed validation (HAB-SCH-001)."""
    return ScheduleError(ErrorCode.SCH_INVALID)


def _enum(cls: type[_E], raw: object) -> _E:  # noqa: UP047 - code_index.py parses with older Python
    """Return the member of `cls` for a raw value, or raise HAB-SCH-001."""
    try:
        return cls(raw)
    except ValueError:
        raise _invalid() from None


def _number(raw: object, low: int, high: int) -> int:
    """Return a whole number within the range; a bool does not count."""
    if isinstance(raw, bool) or not isinstance(raw, int) or not low <= raw <= high:
        raise _invalid()
    return raw


def parse_time(raw: object) -> time:
    """Return the time of a `HH:MM` text (24 h, no seconds)."""
    if not isinstance(raw, str) or len(raw) != 5 or raw[2] != ":":
        raise _invalid()
    try:
        return time(int(raw[:2]), int(raw[3:]))
    except ValueError:
        raise _invalid() from None


def parse_days(raw: object) -> frozenset[int]:
    """Return the non-empty set of weekdays (0 = Monday)."""
    if not isinstance(raw, list | tuple | set | frozenset) or not raw:
        raise _invalid()
    return frozenset(_number(day, 0, 6) for day in raw)


def parse_when(raw: object) -> When:
    """Return the validated trigger: a time with weekdays, or a sun event with an offset."""
    if not isinstance(raw, Mapping):
        raise _invalid()
    kind = _enum(WhenType, raw.get("type"))
    days = parse_days(raw.get("days"))
    if kind is WhenType.TIME:
        if "offset_min" in raw:
            raise _invalid()
        return When(kind, days, time=parse_time(raw.get("time")))
    if "time" in raw:
        raise _invalid()
    offset = _number(raw.get("offset_min", 0), -MAX_OFFSET_MIN, MAX_OFFSET_MIN)
    return When(kind, days, offset_min=offset)


def parse_name(raw: object) -> str:
    """Return the trimmed name of 1 to 60 characters."""
    if not isinstance(raw, str):
        raise _invalid()
    name = raw.strip()
    if not 1 <= len(name) <= MAX_NAME_LENGTH:
        raise _invalid()
    return name


def parse_action(raw: object) -> Action:
    """Return the validated action."""
    return _enum(Action, raw)


def parse_entities(raw: object) -> tuple[str, ...]:
    """Return 1 to 20 distinct switch entity ids in the given order."""
    if not isinstance(raw, list | tuple) or not 1 <= len(raw) <= MAX_ENTITIES_PER_SCHEDULE:
        raise _invalid()
    entities: dict[str, None] = {}
    for entity_id in raw:
        if (
            not isinstance(entity_id, str)
            or not valid_entity_id(entity_id)
            or split_entity_id(entity_id)[0] != SCHEDULE_DOMAIN
        ):
            raise _invalid()
        entities[entity_id] = None
    return tuple(entities)


def parse_enabled(raw: object) -> bool:
    """Return the `enabled` flag; it must be a real boolean."""
    if not isinstance(raw, bool):
        raise _invalid()
    return raw


def new_schedule(owner: str, fields: Mapping[str, Any], now: datetime | None = None) -> Schedule:
    """Return a new schedule with a fresh id after validating `name`, `when`, `action`, `entities`.

    The optional `enabled` defaults to true.
    """
    created = now or dt_util.utcnow()
    return Schedule(
        id=uuid.uuid4().hex,
        owner=owner,
        name=parse_name(fields.get("name")),
        enabled=parse_enabled(fields.get("enabled", True)),
        when=parse_when(fields.get("when")),
        action=parse_action(fields.get("action")),
        entities=parse_entities(fields.get("entities")),
        created_at=created,
        updated_at=created,
    )


def _parse_moment(raw: object) -> datetime:
    """Return the datetime of a stored ISO text."""
    moment = dt_util.parse_datetime(raw) if isinstance(raw, str) else None
    if moment is None:
        raise _invalid()
    return moment


def _parse_paused(raw: object) -> Paused | None:
    """Return the stored pause, or None."""
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise _invalid()
    return Paused(_enum(PauseReason, raw.get("reason")), _parse_moment(raw.get("at")))


def _parse_last_run(raw: object) -> LastRun | None:
    """Return the stored last run, or None."""
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise _invalid()
    code = raw.get("code")
    if code is not None and not isinstance(code, str):
        raise _invalid()
    return LastRun(_parse_moment(raw.get("at")), _enum(RunResult, raw.get("result")), code)


def schedule_from_dict(raw: object) -> Schedule:
    """Return the schedule of a stored dict, or raise HAB-SCH-001 if it is damaged."""
    if not isinstance(raw, Mapping):
        raise _invalid()
    owner = raw.get("owner")
    schedule_id = raw.get("id")
    enabled = raw.get("enabled")
    if (
        not isinstance(owner, str)
        or not isinstance(schedule_id, str)
        or not isinstance(enabled, bool)
    ):
        raise _invalid()
    return Schedule(
        id=schedule_id,
        owner=owner,
        name=parse_name(raw.get("name")),
        enabled=enabled,
        when=parse_when(raw.get("when")),
        action=parse_action(raw.get("action")),
        entities=parse_entities(raw.get("entities")),
        created_at=_parse_moment(raw.get("created_at")),
        updated_at=_parse_moment(raw.get("updated_at")),
        paused=_parse_paused(raw.get("paused")),
        last_run=_parse_last_run(raw.get("last_run")),
    )

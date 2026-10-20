"""Activity text of a `haac_bridge_action` event (concept 21.4)."""

from collections.abc import Mapping
from typing import Any

ACTION_CALL = "call_service"
ACTION_SCHEDULE = "schedule_run"
ACTION_SKIPPED = "schedule_skipped"

_VERBS = {
    "turn_on": ("turned on", "turn on"),
    "turn_off": ("turned off", "turn off"),
    "toggle": ("toggled", "toggle"),
}
_VALUE_KEYS = (
    "temperature",
    "hvac_mode",
    "humidity",
    "fan_mode",
    "preset_mode",
    "swing_mode",
    "swing_horizontal_mode",
)


def _phrases(service: str) -> tuple[str, str]:
    """Return the past tense ("turned on") and the plain form ("turn on") of a service."""
    plain = service.replace("_", " ")
    return _VERBS.get(service, (plain, plain))


def _value_of(data: Mapping[str, Any]) -> str | None:
    """Return the value a climate call set, e.g. `21.5` or `heat`, or None."""
    for key in _VALUE_KEYS:
        if key in data:
            return str(data[key])
    low, high = data.get("target_temp_low"), data.get("target_temp_high")
    return f"{low} to {high}" if low is not None and high is not None else None


def _origin(event: Mapping[str, Any]) -> str:
    """Return who acted: "via HAAC app (Pixel 8)" or "by a schedule"."""
    if event.get("action") == ACTION_SCHEDULE:
        return "by a schedule"
    if event.get("source") != "app":
        return "via HAAC Bridge"
    client = event.get("client")
    return f"via HAAC app ({client})" if client else "via HAAC app"


def describe(event: Mapping[str, Any]) -> str:
    """Return the message the Activity page shows for an event."""
    if event.get("action") == ACTION_SKIPPED:
        return "HAAC schedule did not run"
    past, plain = _phrases(str(event.get("service", "")))
    if event.get("result") != "ok":
        return f"{plain} failed {_origin(event)}"
    value = _value_of(event.get("data") or {})
    return f"{past}{f' to {value}' if value else ''} {_origin(event)}"

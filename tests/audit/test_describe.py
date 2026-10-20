"""Tests for the texts of the Activity page (concept 21.4)."""

from custom_components.haac_bridge.audit.describe import describe


def test_a_switch_turned_on_by_the_app() -> None:
    event = {
        "action": "call_service",
        "result": "ok",
        "service": "turn_on",
        "source": "app",
        "client": "Pixel 8",
    }
    assert describe(event) == "turned on via HAAC app (Pixel 8)"


def test_a_climate_value() -> None:
    event = {
        "action": "call_service",
        "result": "ok",
        "service": "set_temperature",
        "source": "app",
        "data": {"temperature": 21.5},
    }
    assert describe(event) == "set temperature to 21.5 via HAAC app"


def test_a_call_from_another_client() -> None:
    event = {"action": "call_service", "result": "ok", "service": "turn_off", "source": "other"}
    assert describe(event) == "turned off via HAAC Bridge"


def test_a_failure() -> None:
    event = {"action": "call_service", "result": "failed", "service": "turn_on", "source": "app"}
    assert describe(event) == "turn on failed via HAAC app"


def test_a_schedule_and_a_skipped_run() -> None:
    run = {"action": "schedule_run", "result": "ok", "service": "turn_off"}
    assert describe(run) == "turned off by a schedule"
    assert describe({"action": "schedule_skipped", "result": "skipped"}) == (
        "HAAC schedule did not run"
    )

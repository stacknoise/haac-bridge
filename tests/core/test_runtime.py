"""Tests for the no-op stand-ins of the deactivation store and the run log (concept 7.5, 19.11)."""

from datetime import UTC, datetime

from custom_components.haac_bridge.core.runtime import NoDisabledEntities, NoRunLog
from custom_components.haac_bridge.schedules.model import RunEntry, RunResult, RunTrigger


def test_no_disabled_entities_disables_nothing() -> None:
    disabled = NoDisabledEntities()
    assert disabled.is_disabled("user", "switch.lamp") is False
    assert disabled.entities_of("user") == {}


def test_no_run_log_drops_entries() -> None:
    entry = RunEntry(
        "id", "user", "Name", datetime.now(UTC), RunResult.OK, None, RunTrigger.MANUAL, False, True
    )
    assert NoRunLog().record(entry) is None

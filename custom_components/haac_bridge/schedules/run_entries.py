"""Entries for the run log written outside a normal run: removals and missed runs (concept 19.10, 19.11)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from ..core.runtime import get_data
from .model import LastRun, RunEntry, RunTrigger, Schedule


def record_run(
    hass: HomeAssistant,
    schedule: Schedule,
    run: LastRun,
    trigger: RunTrigger,
    *,
    removed: bool,
) -> None:
    """Write a run of the schedule to the run log; `removed` says the schedule is deleted after it."""
    entry = RunEntry(
        schedule_id=schedule.id,
        owner=schedule.owner,
        name=schedule.name,
        at=run.at,
        result=run.result,
        code=run.code,
        trigger=trigger,
        removed=removed,
        notify=schedule.notify,
    )
    get_data(hass).run_log.record(entry)

"""The log of schedule runs in `.storage/haac_bridge.schedule_runs` (concept 19.11)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any
import uuid

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from ..const import (
    MAX_RUN_LOG_PER_OWNER,
    RUN_LOG_RETENTION,
    RUN_LOG_STORE_KEY,
    RUN_LOG_STORE_VERSION,
    RUN_RESULT_SAVE_DELAY,
)
from .model import RunEntry, RunResult, RunTrigger

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LoggedRun:
    """A run in the log: the entry as the runner reported it, numbered by the log."""

    seq: int
    entry: RunEntry

    def to_dict(self) -> dict[str, Any]:
        """Return the stored and sent form of the run (concept 19.11)."""
        entry = self.entry
        return {
            "seq": self.seq,
            "schedule_id": entry.schedule_id,
            "owner": entry.owner,
            "name": entry.name,
            "at": entry.at.isoformat(),
            "result": entry.result.value,
            "code": entry.code,
            "trigger": entry.trigger.value,
            "removed": entry.removed,
            "notify": entry.notify,
        }


def _logged_run_from_dict(raw: Any) -> LoggedRun | None:
    """Return the run of a stored entry, or None if the entry is damaged."""
    try:
        at = dt_util.parse_datetime(raw["at"])
        if at is None or isinstance(raw["seq"], bool) or not isinstance(raw["seq"], int):
            return None
        code = raw["code"]
        flags = (raw["removed"], raw["notify"])
        if (code is not None and not isinstance(code, str)) or not all(
            isinstance(flag, bool) for flag in flags
        ):
            return None
        entry = RunEntry(
            schedule_id=str(raw["schedule_id"]),
            owner=str(raw["owner"]),
            name=str(raw["name"]),
            at=at,
            result=RunResult(raw["result"]),
            code=code,
            trigger=RunTrigger(raw["trigger"]),
            removed=flags[0],
            notify=flags[1],
        )
    except KeyError, TypeError, ValueError:
        return None
    return LoggedRun(raw["seq"], entry)


class ScheduleRunLog:
    """Keeps the runs of all schedules in memory and writes them to storage with a short delay.

    `log_id` is new whenever the log starts empty, so an app that holds a cursor of an older log
    knows to start over (concept 19.11).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Create an empty log; call `async_load` before use."""
        self._store: Store[dict[str, Any]] = Store(
            hass, RUN_LOG_STORE_VERSION, RUN_LOG_STORE_KEY, private=True
        )
        self.log_id = str(uuid.uuid4())
        self._seq = 0
        self._runs: list[LoggedRun] = []

    async def async_load(self) -> None:
        """Read the log from storage; damaged entries are dropped, a missing file starts a new log."""
        stored = await self._store.async_load()
        self._runs = []
        if not isinstance(stored, dict) or not isinstance(stored.get("log_id"), str):
            self.log_id = str(uuid.uuid4())
            self._seq = 0
            return
        self.log_id = stored["log_id"]
        seq = stored.get("seq")
        self._seq = seq if isinstance(seq, int) and not isinstance(seq, bool) else 0
        for raw in stored.get("entries", []):
            if (run := _logged_run_from_dict(raw)) is None:
                _LOGGER.warning("Dropping a damaged entry of the schedule run log")
                continue
            self._runs.append(run)
        self._seq = max([self._seq, *(run.seq for run in self._runs)])
        self._prune(dt_util.utcnow())

    @property
    def last_seq(self) -> int:
        """Return the number of the newest entry of the log, 0 for a log that never had one."""
        return self._seq

    def record(self, entry: RunEntry) -> None:
        """Append the entry of a finished or missed run and write the log soon."""
        self._seq += 1
        self._runs.append(LoggedRun(self._seq, entry))
        self._prune(dt_util.utcnow())
        self._store.async_delay_save(self._data_to_save, RUN_RESULT_SAVE_DELAY)

    def runs_of(self, owner: str, after_seq: int = 0) -> list[dict[str, Any]]:
        """Return the owner's own entries with `seq` above `after_seq`, oldest first."""
        return [
            run.to_dict() for run in self._runs if run.entry.owner == owner and run.seq > after_seq
        ]

    def last_seq_of(self, owner: str) -> int:
        """Return the number of the owner's newest entry, 0 if the owner has none."""
        return max((run.seq for run in self._runs if run.entry.owner == owner), default=0)

    def owners(self) -> set[str]:
        """Return the owners that have entries in the log."""
        return {run.entry.owner for run in self._runs}

    def remove_owners(self, owner_ids: set[str]) -> bool:
        """Delete all entries of these owners and write the log soon; return whether any existed."""
        kept = [run for run in self._runs if run.entry.owner not in owner_ids]
        if len(kept) == len(self._runs):
            return False
        self._runs = kept
        self._store.async_delay_save(self._data_to_save, RUN_RESULT_SAVE_DELAY)
        return True

    async def async_remove_file(self) -> None:
        """Forget all entries and delete the storage file when the config entry is removed."""
        self._runs = []
        self._seq = 0
        await self._store.async_remove()

    def _prune(self, now: datetime) -> None:
        """Drop entries older than the retention and the oldest ones above the limit per owner."""
        oldest = now - RUN_LOG_RETENTION
        kept = [run for run in self._runs if run.entry.at >= oldest]
        per_owner: dict[str, int] = {}
        newest_first: list[LoggedRun] = []
        for run in reversed(kept):
            count = per_owner.get(run.entry.owner, 0) + 1
            per_owner[run.entry.owner] = count
            if count <= MAX_RUN_LOG_PER_OWNER:
                newest_first.append(run)
        self._runs = newest_first[::-1]

    def _data_to_save(self) -> dict[str, Any]:
        """Return the stored form of the log."""
        return {
            "log_id": self.log_id,
            "seq": self._seq,
            "entries": [run.to_dict() for run in self._runs],
        }

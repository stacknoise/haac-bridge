"""Persistent storage of the schedules in `.storage/haac_bridge.schedules` (concept 19.2)."""

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ..const import SCHEDULE_STORE_KEY, SCHEDULE_STORE_VERSION
from ..core.errors import ErrorCode, ScheduleError
from .model import Schedule, schedule_from_dict

_LOGGER = logging.getLogger(__name__)


class ScheduleStore:
    """Holds all schedules in memory and writes them to storage after every change."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Create an empty store; call `async_load` before use."""
        self._store: Store[dict[str, Any]] = Store(
            hass, SCHEDULE_STORE_VERSION, SCHEDULE_STORE_KEY, private=True
        )
        self._schedules: dict[str, Schedule] = {}

    async def async_load(self) -> None:
        """Read the schedules from storage; a damaged entry is skipped and logged once."""
        stored = await self._store.async_load() or {}
        self._schedules = {}
        for raw in stored.get("schedules", []):
            try:
                schedule = schedule_from_dict(raw)
            except ScheduleError as err:
                _LOGGER.warning("Skipping a damaged schedule in storage (%s)", err.code.value)
                continue
            self._schedules[schedule.id] = schedule

    @property
    def schedules(self) -> list[Schedule]:
        """Return all schedules, oldest first."""
        return sorted(self._schedules.values(), key=lambda item: item.created_at)

    def get(self, schedule_id: str) -> Schedule | None:
        """Return the schedule with this id, or None."""
        return self._schedules.get(schedule_id)

    def by_owner(self, owner: str) -> list[Schedule]:
        """Return the schedules of one HA user, oldest first."""
        return [item for item in self.schedules if item.owner == owner]

    async def async_add(self, schedule: Schedule) -> None:
        """Add a new schedule and save."""
        self._schedules[schedule.id] = schedule
        await self._async_save()

    async def async_replace(self, schedule: Schedule) -> None:
        """Replace an existing schedule as a whole and save; an unknown id raises HAB-SCH-003."""
        if schedule.id not in self._schedules:
            raise ScheduleError(ErrorCode.SCH_NOT_FOUND)
        self._schedules[schedule.id] = schedule
        await self._async_save()

    async def async_remove(self, schedule_ids: Iterable[str]) -> list[Schedule]:
        """Remove the schedules with these ids, save once and return what was removed."""
        removed = [
            self._schedules.pop(schedule_id)
            for schedule_id in list(schedule_ids)
            if schedule_id in self._schedules
        ]
        if removed:
            await self._async_save()
        return removed

    async def _async_save(self) -> None:
        """Write all schedules to storage."""
        await self._store.async_save({"schedules": [item.to_dict() for item in self.schedules]})

    async def async_remove_file(self) -> None:
        """Delete the storage file when the config entry of the bridge is removed."""
        self._schedules = {}
        await self._store.async_remove()

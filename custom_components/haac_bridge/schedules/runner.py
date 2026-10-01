"""Runs one schedule: re-checks owner and exposure, switches the entities as the owner (concept 19.3)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..core.errors import ErrorCode, HaacBridgeError
from ..core.runtime import get_data
from ..services.call_factory import async_execute
from .model import LastRun, Paused, PauseReason, RunResult, Schedule
from .store import ScheduleStore

_LOGGER = logging.getLogger(__name__)

RETRY_DELAY_SECONDS = 30
"""Entities that are unavailable at run time are tried once more after this long (concept 19.3)."""

UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class RunHooks:
    """What the runner asks the manager to do: remove schedules, re-plan one, announce a change."""

    remove: Callable[[list[str]], Awaitable[None]]
    replan: Callable[[str], Awaitable[None]]
    changed: Callable[[], None]


class ScheduleRunner:
    """Executes schedules one at a time per schedule."""

    def __init__(self, hass: HomeAssistant, store: ScheduleStore, hooks: RunHooks) -> None:
        """Keep what a run needs."""
        self._hass = hass
        self._store = store
        self._hooks = hooks
        self._locks: dict[str, asyncio.Lock] = {}

    async def async_run(self, schedule_id: str) -> None:
        """Run a schedule now; a run of the same schedule that is still going on finishes first."""
        lock = self._locks.setdefault(schedule_id, asyncio.Lock())
        async with lock:
            await self._async_run_locked(schedule_id)
        if self._store.get(schedule_id) is None:
            self._locks.pop(schedule_id, None)

    async def _async_run_locked(self, schedule_id: str) -> None:
        """Validate the owner and the exposure, then switch and record the result."""
        schedule = self._store.get(schedule_id)
        if schedule is None:
            return
        user = await self._hass.auth.async_get_user(schedule.owner)
        exposure = get_data(self._hass).exposure
        if user is None or not exposure.is_configured(user):
            await self._hooks.remove([schedule.id])
            return
        if not user.is_active:
            await self._async_pause(schedule.id, PauseReason.OWNER_INACTIVE)
            return
        targets = [entity for entity in schedule.entities if exposure.is_exposed(user, entity)]
        if not targets:
            failed = LastRun(dt_util.utcnow(), RunResult.FAILED, ErrorCode.SCH_RUN_FAILED.value)
            await self._async_pause(schedule.id, PauseReason.NO_ENTITIES, failed)
            return
        done = await self._async_switch_all(user, schedule, targets)
        await self._async_record(schedule.id, _result(done, len(schedule.entities)))

    async def _async_switch_all(self, user: User, schedule: Schedule, targets: list[str]) -> int:
        """Switch the entities, the unavailable ones after a short wait; return how many worked."""
        service = schedule.action.value
        ready = [entity for entity in targets if not self._is_unavailable(entity)]
        later = [entity for entity in targets if entity not in ready]
        done = sum([await self._async_switch_one(user, entity, service) for entity in ready])
        if later:
            await self._async_wait_before_retry()
            done += sum(
                [
                    await self._async_switch_one(user, entity, service)
                    for entity in later
                    if not self._is_unavailable(entity)
                ]
            )
        return done

    async def _async_wait_before_retry(self) -> None:
        """Wait before unavailable entities are tried once more."""
        await asyncio.sleep(RETRY_DELAY_SECONDS)

    async def _async_switch_one(self, user: User, entity_id: str, service: str) -> int:
        """Call the service for one entity as the owner; return 1 if it worked, else 0."""
        data = get_data(self._hass)
        try:
            call = data.services.create(data.exposure, user, entity_id, service, {})
            await async_execute(self._hass, call)
        except HaacBridgeError as err:
            _LOGGER.warning("%s while a schedule switched %s", err.code, entity_id)
            return 0
        return 1

    def _is_unavailable(self, entity_id: str) -> bool:
        """Return True if the entity's state is `unavailable`."""
        state = self._hass.states.get(entity_id)
        return state is not None and state.state == UNAVAILABLE

    async def _async_record(self, schedule_id: str, result: RunResult) -> None:
        """Store the outcome of a run on the schedule as it is now."""
        code = None if result is RunResult.OK else ErrorCode.SCH_RUN_FAILED.value
        await self._async_update(schedule_id, last_run=LastRun(dt_util.utcnow(), result, code))

    async def _async_pause(
        self, schedule_id: str, reason: PauseReason, last_run: LastRun | None = None
    ) -> None:
        """Pause a schedule for a reason, optionally with a failed last run, and stop its timer."""
        paused = Paused(reason, dt_util.utcnow())
        await self._async_update(schedule_id, paused=paused, last_run=last_run)
        await self._hooks.replan(schedule_id)

    async def _async_update(
        self,
        schedule_id: str,
        *,
        last_run: LastRun | None = None,
        paused: Paused | None = None,
    ) -> None:
        """Set `last_run` and `paused` (those that are given) on the current version and announce it."""
        current = self._store.get(schedule_id)
        if current is None:
            return
        changes = {
            name: value
            for name, value in (("last_run", last_run), ("paused", paused))
            if value is not None
        }
        await self._store.async_replace(current.with_changes(**changes))
        self._hooks.changed()


def _result(done: int, total: int) -> RunResult:
    """Return `ok` if every entity worked, `partial` if some did and `failed` if none did."""
    if done == total:
        return RunResult.OK
    return RunResult.PARTIAL if done else RunResult.FAILED

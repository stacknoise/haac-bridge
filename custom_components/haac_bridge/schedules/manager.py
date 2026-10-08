"""ScheduleManager: store, planner and runner together, and the operations of the commands (concept 19.4)."""

from __future__ import annotations

import hashlib
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from ..const import MAX_SCHEDULES_PER_USER, SIGNAL_SCHEDULES_CHANGED
from ..core.errors import ErrorCode, ScheduleError
from ..core.runtime import get_data
from .model import (
    Paused,
    PauseReason,
    Schedule,
    new_schedule,
    parse_action,
    parse_enabled,
    parse_entities,
    parse_name,
    parse_when,
)
from .planner import SchedulePlanner
from .runner import RunHooks, ScheduleRunner
from .store import ScheduleStore
from .triggers import TriggerFactory

SCOPE_OWN = "own"
SCOPE_ALL = "all"


class ScheduleManager:
    """Creates, changes, deletes, lists and runs schedules for the commands, as a given user."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Wire the store, the planner and the runner; call `async_load` and `async_start` next."""
        self._hass = hass
        # False until the config entry has loaded the UI users, and while it is unloaded or disabled.
        # Runs wait and sweeps do nothing then, so UI users never look unconfigured by mistake.
        self.users_ready = False
        self.store = ScheduleStore(hass)
        self.planner = SchedulePlanner(
            hass, self.store, TriggerFactory(hass), self._async_run_due, self.notify
        )
        hooks = RunHooks(
            self.async_remove, self.planner.async_plan, self.notify, lambda: self.users_ready
        )
        self.runner = ScheduleRunner(hass, self.store, hooks)

    async def async_load(self) -> None:
        """Read the schedules from storage."""
        await self.store.async_load()

    async def async_start(self) -> None:
        """Start planning; call when Home Assistant has started."""
        await self.planner.async_start()

    @callback
    def async_stop(self) -> None:
        """Cancel all timers."""
        self.planner.async_stop()

    @callback
    def notify(self) -> None:
        """Tell subscribers that a schedule changed, ran, was paused or was removed."""
        async_dispatcher_send(self._hass, SIGNAL_SCHEDULES_CHANGED)

    async def _async_run_due(self, schedule_id: str) -> None:
        """Run a schedule whose time has come."""
        await self.runner.async_run(schedule_id)

    @staticmethod
    def scope_of(user: User) -> str:
        """Return `all` for admins, who see every schedule, and `own` for everybody else."""
        return SCOPE_ALL if user.is_admin else SCOPE_OWN

    def visible_to(self, user: User) -> list[Schedule]:
        """Return the schedules the user may see: all for admins, their own for others."""
        return self.store.schedules if user.is_admin else self.store.by_owner(user.id)

    def revision_for(self, user: User) -> str:
        """Return a hash over the visible schedules (id, version, pause, last run) and the scope."""
        digest = hashlib.sha256(self.scope_of(user).encode())
        for schedule in sorted(self.visible_to(user), key=lambda item: item.id):
            paused = schedule.paused
            last_run = schedule.last_run
            parts = (
                schedule.id,
                schedule.updated_at.isoformat(),
                f"{paused.reason.value}@{paused.at.isoformat()}" if paused else "",
                last_run.at.isoformat() if last_run else "",
            )
            digest.update(("\t".join(parts) + "\n").encode())
        return digest.hexdigest()

    async def async_describe(self, schedule: Schedule, user: User) -> dict[str, Any]:
        """Return the stored form plus the owner's name, the computed next run and whether `user` owns it."""
        owner = await self._hass.auth.async_get_user(schedule.owner)
        planned = self.planner.planned_run(schedule.id)
        return {
            **schedule.to_dict(),
            "owner_name": owner.name if owner else None,
            "own": schedule.owner == user.id,
            "next_run": planned.isoformat() if planned else None,
        }

    async def async_list(self, user: User) -> dict[str, Any]:
        """Return the revision, the scope and the visible schedules."""
        return {
            "revision": self.revision_for(user),
            "scope": self.scope_of(user),
            "schedules": [await self.async_describe(item, user) for item in self.visible_to(user)],
        }

    async def async_create(self, user: User, fields: dict[str, Any]) -> Schedule:
        """Create a schedule owned by `user` after validating it and the exposure of its entities."""
        if len(self.store.by_owner(user.id)) >= MAX_SCHEDULES_PER_USER:
            raise ScheduleError(ErrorCode.SCH_LIMIT)
        schedule = new_schedule(user.id, fields)
        self._check_exposed(user, schedule.entities)
        await self.store.async_add(schedule)
        await self.planner.async_plan(schedule.id)
        self.notify()
        return schedule

    async def async_update(
        self, user: User, schedule_id: str, updated_at: str, fields: dict[str, Any]
    ) -> Schedule:
        """Change a schedule the user may edit; `updated_at` must be that of the edited version."""
        owner = await self._hass.auth.async_get_user(self._require(schedule_id).owner)
        current = self._require(schedule_id)
        self._require_access(user, current)
        if dt_util.parse_datetime(updated_at) != current.updated_at:
            raise ScheduleError(ErrorCode.SCH_CONFLICT)
        changes = self._parse_changes(user, current, fields)
        updated = self._without_ended_pause(
            current.with_changes(updated_at=dt_util.utcnow(), **changes), owner
        )
        await self.store.async_replace(updated)
        await self.planner.async_plan(updated.id)
        self.notify()
        return updated

    async def async_set_enabled(self, schedule_id: str, *, enabled: bool) -> None:
        """Enable or disable a schedule, as its `enabled` switch in HA does (concept 19.5)."""
        schedule = self._require(schedule_id)
        if schedule.enabled == enabled:
            return
        await self.store.async_replace(
            schedule.with_changes(enabled=enabled, updated_at=dt_util.utcnow())
        )
        await self.planner.async_plan(schedule_id)
        self.notify()

    async def async_wipe(self) -> None:
        """Delete every schedule and the storage file; called when the config entry is removed."""
        schedule_ids = [schedule.id for schedule in self.store.schedules]
        await self.store.async_remove_file()
        for schedule_id in schedule_ids:
            await self.planner.async_plan(schedule_id)
        self.notify()

    async def async_delete(self, user: User, schedule_id: str) -> None:
        """Delete a schedule the user may edit; an unknown id is not an error."""
        schedule = self.store.get(schedule_id)
        if schedule is None:
            return
        self._require_access(user, schedule)
        await self.async_remove([schedule_id])

    async def async_run_now(self, user: User, schedule_id: str) -> None:
        """Run a schedule once now, as its owner, without changing the plan."""
        self._require_access(user, self._require(schedule_id))
        await self.runner.async_run(schedule_id)

    async def async_sweep(self, owner_id: str | None = None) -> None:
        """Delete the schedules of users who are gone or not configured, pause those of inactive ones.

        Runs after every change of the user list and at setup (concept 19.6.3). With `owner_id`
        only that user's schedules are looked at. Everything is saved once and announced once.
        Does nothing while the UI users are not loaded (`users_ready` is False).
        """
        if not self.users_ready:
            return
        users = {user.id: user for user in await self._hass.auth.async_get_users()}
        exposure = get_data(self._hass).exposure
        replace: list[Schedule] = []
        remove: list[str] = []
        for schedule in self.store.schedules:
            if owner_id is not None and schedule.owner != owner_id:
                continue
            owner = users.get(schedule.owner)
            if owner is None or not exposure.is_configured(owner):
                remove.append(schedule.id)
                continue
            updated = self._with_owner_state(schedule, owner)
            if updated != schedule:
                replace.append(updated)
        if not replace and not remove:
            return
        await self.store.async_apply_changes(replace, remove)
        for schedule_id in [*(item.id for item in replace), *remove]:
            await self.planner.async_plan(schedule_id)
        self.notify()

    async def async_remove_owner(self, owner_id: str) -> None:
        """Delete every schedule of a user, as when the HA user was deleted (concept 19.6.1)."""
        await self.async_remove([item.id for item in self.store.by_owner(owner_id)])

    async def async_remove(self, schedule_ids: list[str]) -> None:
        """Remove schedules, stop their timers and tell subscribers."""
        removed = await self.store.async_remove(schedule_ids)
        for schedule in removed:
            await self.planner.async_plan(schedule.id)
        if removed:
            self.notify()

    def _require(self, schedule_id: str) -> Schedule:
        """Return the schedule or raise HAB-SCH-003."""
        schedule = self.store.get(schedule_id)
        if schedule is None:
            raise ScheduleError(ErrorCode.SCH_NOT_FOUND)
        return schedule

    @staticmethod
    def _require_access(user: User, schedule: Schedule) -> None:
        """Allow the owner and admins; anybody else gets HAB-SCH-006."""
        if schedule.owner != user.id and not user.is_admin:
            raise ScheduleError(ErrorCode.SCH_NOT_ALLOWED)

    def _check_exposed(self, user: User, entities: tuple[str, ...]) -> None:
        """Require every entity to be exposed to the user; the bridge's own entities never are."""
        exposure = get_data(self._hass).exposure
        if not all(exposure.is_exposed(user, entity_id) for entity_id in entities):
            raise ScheduleError(ErrorCode.SCH_INVALID)

    def _parse_changes(
        self, user: User, schedule: Schedule, fields: dict[str, Any]
    ) -> dict[str, Any]:
        """Return the validated changes of an update; only the owner may change the entities."""
        parsers = {
            "name": parse_name,
            "enabled": parse_enabled,
            "when": parse_when,
            "action": parse_action,
        }
        changes = {name: parse(fields[name]) for name, parse in parsers.items() if name in fields}
        if "entities" in fields:
            entities = parse_entities(fields["entities"])
            if entities != schedule.entities:
                if user.id != schedule.owner:
                    raise ScheduleError(ErrorCode.SCH_NOT_ALLOWED)
                self._check_exposed(user, entities)
                changes["entities"] = entities
        return changes

    def _with_owner_state(self, schedule: Schedule, owner: User) -> Schedule:
        """Return the schedule paused if its owner is inactive, or resumed if its pause has ended."""
        if owner.is_active:
            return self._without_ended_pause(schedule, owner)
        paused = schedule.paused
        if paused is not None and paused.reason is PauseReason.OWNER_INACTIVE:
            return schedule
        return schedule.with_changes(paused=Paused(PauseReason.OWNER_INACTIVE, dt_util.utcnow()))

    def _without_ended_pause(self, schedule: Schedule, owner: User | None) -> Schedule:
        """Return the schedule without a pause whose cause is gone (concept 19.5)."""
        paused = schedule.paused
        if paused is None or owner is None:
            return schedule
        exposure = get_data(self._hass).exposure
        ended = (paused.reason is PauseReason.OWNER_INACTIVE and owner.is_active) or (
            paused.reason is PauseReason.NO_ENTITIES
            and any(exposure.is_exposed(owner, entity_id) for entity_id in schedule.entities)
        )
        return schedule.with_changes(paused=None) if ended else schedule

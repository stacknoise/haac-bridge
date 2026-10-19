"""ScheduleManager: store, planner and runner together, and the operations of the commands (concept 19.4)."""

from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from ..const import (
    MAX_SCHEDULES_PER_USER,
    RUN_NOW_COOLDOWN,
    SIGNAL_SCHEDULE_CHANGED,
    SIGNAL_SCHEDULES_CHANGED,
)
from ..core.errors import ErrorCode, RequestError, ScheduleError
from ..core.runtime import get_data
from ..disabling.schedules import blocked_by, require_unblocked
from .model import (
    Paused,
    PauseReason,
    RepeatFreq,
    Schedule,
    check_repeat,
    new_schedule,
    parse_action,
    parse_enabled,
    parse_entities,
    parse_name,
    parse_notify,
    parse_repeat,
    parse_when,
)
from .planner import SchedulePlanner
from .repairs import async_sync_unreadable_issue
from .run_log import ScheduleRunLog
from .runner import RunHooks, ScheduleRunner
from .store import ScheduleStore
from .triggers import TriggerFactory

SCOPE_OWN = "own"
SCOPE_ALL = "all"


def _parse_version(updated_at: str) -> datetime:
    """Return the version a client sends back, or raise HAB-WS-001 if it is no date and time."""
    try:
        version = dt_util.parse_datetime(updated_at)
    except ValueError:
        version = None
    if version is None:
        raise RequestError(ErrorCode.WS_INVALID_REQUEST)
    return version


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
            hass,
            self.store,
            TriggerFactory(hass),
            self._async_run_due,
            self.notify,
        )
        self.planner.on_missed = self._async_log_missed
        hooks = RunHooks(
            self.async_remove,
            self.planner.async_plan,
            self.notify,
            lambda: self.users_ready,
            self.planner.ends_with_run,
        )
        self.run_log = ScheduleRunLog(hass)
        self.runner = ScheduleRunner(hass, self.store, hooks, self.run_log)
        self._manual_runs: dict[str, float] = {}

    async def async_load(self) -> None:
        """Read the schedules and the run log from storage and report entries that could not be read."""
        await self.store.async_load()
        await self.run_log.async_load()
        async_sync_unreadable_issue(self._hass, self.store.unreadable_count)

    async def async_start(self) -> None:
        """Start planning; call when Home Assistant has started."""
        await self.planner.async_start()

    @callback
    def async_stop(self) -> None:
        """Cancel all timers and the runs still going on in the background."""
        self.planner.async_stop()
        self.runner.async_cancel_all()

    @callback
    def notify(self, *schedule_ids: str) -> None:
        """Tell subscribers that schedules changed, ran, were paused or were removed.

        Subscriptions and the entity manager get one general signal; the entities of each named
        schedule get their own signal, so a run does not rewrite the state of every schedule.
        """
        async_dispatcher_send(self._hass, SIGNAL_SCHEDULES_CHANGED)
        for schedule_id in schedule_ids:
            async_dispatcher_send(self._hass, SIGNAL_SCHEDULE_CHANGED.format(schedule_id))

    async def _async_run_due(self, schedule_id: str) -> None:
        """Run a schedule whose time has come."""
        await self.runner.async_run(schedule_id)

    async def _async_log_missed(self, schedule: Schedule, at: datetime, *, last: bool) -> None:
        """Log a run HA missed; if it was the last one, the schedule is removed (concept 19.10)."""
        self.runner.log_missed(schedule, at, removed=last)
        if last:
            await self.async_remove([schedule.id])
        else:
            self.notify(schedule.id)

    @staticmethod
    def scope_of(user: User) -> str:
        """Return `all` for admins, who see every schedule, and `own` for everybody else."""
        return SCOPE_ALL if user.is_admin else SCOPE_OWN

    def visible_to(self, user: User) -> list[Schedule]:
        """Return the schedules the user may see: all for admins, their own for others."""
        return self.store.schedules if user.is_admin else self.store.by_owner(user.id)

    def revision_for(self, user: User) -> str:
        """Return a hash over the visible schedules, the scope and the caller's newest run log entry.

        Per schedule: id, version, `notify`, pause, last run and next run (concept 11.2, 19.11).
        """
        digest = hashlib.sha256(self.scope_of(user).encode())
        digest.update(f"runs\t{self.run_log.last_seq_of(user.id)}\n".encode())
        for schedule in sorted(self.visible_to(user), key=lambda item: item.id):
            paused = schedule.paused
            last_run = schedule.last_run
            planned = self.planner.planned_run(schedule.id)
            parts = (
                schedule.id,
                schedule.updated_at.isoformat(),
                str(schedule.notify),
                f"{paused.reason.value}@{paused.at.isoformat()}" if paused else "",
                last_run.at.isoformat() if last_run else "",
                planned.isoformat() if planned else "",
            )
            digest.update(("\t".join(parts) + "\n").encode())
        return digest.hexdigest()

    def runs_for(self, user: User, log_id: str | None, after_seq: int) -> dict[str, Any]:
        """Return `log_id`, `last_seq` and the user's own entries after the cursor (concept 19.11).

        Admins get only their own entries as well. A `log_id` other than the log's own means the
        app holds a cursor of an older log, so every entry is returned.
        """
        after = after_seq if log_id == self.run_log.log_id else 0
        return {
            "log_id": self.run_log.log_id,
            "last_seq": self.run_log.last_seq,
            "runs": self.run_log.runs_of(user.id, after),
        }

    async def async_describe(self, schedule: Schedule, user: User) -> dict[str, Any]:
        """Return the stored form plus the owner's name, the computed next run and whether `user` owns it."""
        owner = await self._hass.auth.async_get_user(schedule.owner)
        planned = self.planner.planned_run(schedule.id)
        return {
            **schedule.to_dict(),
            "owner_name": owner.name if owner else None,
            "own": schedule.owner == user.id,
            "blocked_by": blocked_by(get_data(self._hass).disabled, schedule),
            "next_run": planned.isoformat() if planned else None,
            "next_runs": [run.isoformat() for run in self.planner.next_runs(schedule)],
            "expired": self.planner.is_expired(schedule),
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
        self._require_unblocked_if_enabled(schedule)
        await self.store.async_add(schedule)
        await self.planner.async_plan(schedule.id)
        self.notify(schedule.id)
        return schedule

    async def async_update(
        self, user: User, schedule_id: str, updated_at: str, fields: dict[str, Any]
    ) -> Schedule:
        """Change a schedule the user may edit; `updated_at` must be that of the edited version."""
        owner = await self._hass.auth.async_get_user(self._require(schedule_id).owner)
        current = self._require(schedule_id)
        self._require_access(user, current)
        if _parse_version(updated_at) != current.updated_at:
            raise ScheduleError(ErrorCode.SCH_CONFLICT)
        changes = self._parse_changes(user, current, fields)
        updated = self._without_ended_pause(
            current.with_changes(updated_at=dt_util.utcnow(), **changes), owner
        )
        if updated.enabled != current.enabled:
            updated = updated.with_changes(off_reason=None)
        self._require_unblocked_if_enabled(updated)
        if updated.enabled and (not current.enabled or "repeat" in changes or "when" in changes):
            self._require_dates_left(updated)
        await self.store.async_replace(updated)
        await self.planner.async_plan(updated.id)
        self.notify(updated.id)
        return updated

    async def async_set_enabled(self, schedule_id: str, *, enabled: bool) -> None:
        """Enable or disable a schedule, as its `enabled` switch in HA does (concept 19.5).

        Enabling a schedule that contains a deactivated entity is HAB-SCH-008 (concept 7.5).
        """
        schedule = self._require(schedule_id)
        if schedule.enabled == enabled:
            return
        updated = schedule.with_changes(
            enabled=enabled, off_reason=None, updated_at=dt_util.utcnow()
        )
        self._require_unblocked_if_enabled(updated)
        if enabled:
            self._require_dates_left(schedule)
        await self.store.async_replace(updated)
        await self.planner.async_plan(schedule_id)
        self.notify(schedule_id)

    async def async_wipe(self) -> None:
        """Delete every schedule and the storage file; called when the config entry is removed."""
        schedule_ids = [schedule.id for schedule in self.store.schedules]
        await self.store.async_remove_file()
        await self.run_log.async_remove_file()
        async_sync_unreadable_issue(self._hass, 0)
        for schedule_id in schedule_ids:
            await self.planner.async_plan(schedule_id)
        self.notify(*schedule_ids)

    async def async_delete(self, user: User, schedule_id: str) -> None:
        """Delete a schedule the user may edit; an unknown id is not an error."""
        schedule = self.store.get(schedule_id)
        if schedule is None:
            return
        self._require_access(user, schedule)
        await self.async_remove([schedule_id])

    async def async_run_now(self, user: User, schedule_id: str) -> None:
        """Start one run of a schedule now, as its owner, without changing the plan.

        Returns at once; the result arrives with `schedules_changed` like any other run (concept 19.4).
        While the schedule runs, and for RUN_NOW_COOLDOWN seconds after a manual run, HAB-SCH-007.
        """
        schedule = self._require(schedule_id)
        self._require_access(user, schedule)
        require_unblocked(get_data(self._hass).disabled, schedule)
        now = self._hass.loop.time()
        last = self._manual_runs.get(schedule_id)
        if self.runner.is_running(schedule_id) or (
            last is not None and now - last < RUN_NOW_COOLDOWN
        ):
            raise ScheduleError(ErrorCode.SCH_BUSY)
        self._manual_runs[schedule_id] = now
        self.runner.async_run_in_background(schedule_id, user.id)

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
        gone = {
            owner
            for owner in self.run_log.owners()
            if (user := users.get(owner)) is None or not exposure.is_configured(user)
        }
        if owner_id is not None:
            gone &= {owner_id}
        self._remove_runs_of(gone)
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
        changed = [*(item.id for item in replace), *remove]
        for schedule_id in changed:
            await self.planner.async_plan(schedule_id)
        self.notify(*changed)

    async def async_remove_owner(self, owner_id: str) -> None:
        """Delete every schedule and run log entry of a user, as when the HA user was deleted (concept 19.6.1)."""
        await self.async_remove([item.id for item in self.store.by_owner(owner_id)])
        self._remove_runs_of({owner_id})

    async def async_remove(self, schedule_ids: list[str]) -> None:
        """Remove schedules, stop their timers and tell subscribers."""
        removed = await self.store.async_remove(schedule_ids)
        for schedule in removed:
            self._manual_runs.pop(schedule.id, None)
            await self.planner.async_plan(schedule.id)
        if removed:
            self.notify(*(schedule.id for schedule in removed))

    def _remove_runs_of(self, owner_ids: set[str]) -> None:
        """Delete the run log entries of users who are gone or no longer configured (concept 19.11)."""
        if self.run_log.remove_owners(owner_ids):
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

    def _require_dates_left(self, schedule: Schedule) -> None:
        """Raise HAB-SCH-009 if the schedule has no date left, e.g. a one-off in the past (concept 19.10)."""
        if self.planner.is_expired(schedule):
            raise ScheduleError(ErrorCode.SCH_IN_PAST)

    def _require_unblocked_if_enabled(self, schedule: Schedule) -> None:
        """Raise HAB-SCH-008 if the schedule would be enabled although its owner deactivated one of its entities."""
        if schedule.enabled:
            require_unblocked(get_data(self._hass).disabled, schedule)

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
            "action": parse_action,
        }
        changes = {name: parse(fields[name]) for name, parse in parsers.items() if name in fields}
        changes.update(self._parse_dates(schedule, fields))
        if "notify" in fields:
            notify = parse_notify(fields["notify"])
            if notify != schedule.notify:
                if user.id != schedule.owner:
                    raise ScheduleError(ErrorCode.SCH_NOT_ALLOWED)
                changes["notify"] = notify
        if "entities" in fields:
            entities = parse_entities(fields["entities"])
            if entities != schedule.entities:
                if user.id != schedule.owner:
                    raise ScheduleError(ErrorCode.SCH_NOT_ALLOWED)
                self._check_exposed(user, entities)
                changes["entities"] = entities
        return changes

    @staticmethod
    def _parse_dates(schedule: Schedule, fields: dict[str, Any]) -> dict[str, Any]:
        """Return the validated `when` and `repeat` of an update; the weekdays belong to a weekly rule.

        A new date rule gets today as its start date if it has none, and its dates are checked
        against the current time (concept 19.10).
        """
        if "when" not in fields and "repeat" not in fields:
            return {}
        today = dt_util.as_local(dt_util.utcnow()).date()
        repeat = parse_repeat(fields["repeat"], today) if "repeat" in fields else schedule.repeat
        weekly = repeat.freq is RepeatFreq.WEEKLY
        when = (
            parse_when(fields["when"], days_required=weekly) if "when" in fields else schedule.when
        )
        if weekly and not when.days:
            raise ScheduleError(ErrorCode.SCH_INVALID)
        check_repeat(repeat, when)
        return {"when": when, "repeat": repeat}

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

"""AuditEntryFactory: one audit entry per kind of action (concept 18.2, 21.3)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.auth.models import User

from .describe import ACTION_CALL, ACTION_SCHEDULE, ACTION_SKIPPED
from .entry import AuditEntry

if TYPE_CHECKING:
    from ..schedules.model import RunOrigin, Schedule
    from ..services.call_factory import ValidatedServiceCall


def user_label(user: User) -> str:
    """Return `name(first 8 characters of the id)`, which tells users with the same name apart."""
    return f"{user.name}({user.id[:8]})"


def _activity(
    action: str, result: str, call: ValidatedServiceCall, *, client: str | None, source: str | None
) -> dict[str, Any]:
    """Return the data of a `haac_bridge_action` event; `service_data` only for a success (concept 21.4)."""
    event: dict[str, Any] = {
        "action": action,
        "result": result,
        "entity_id": call.entity_id,
        "service": call.service,
    }
    for key, value in (("client", client), ("source", source)):
        if value is not None:
            event[key] = value
    if call.data and result == "ok":
        event["data"] = call.data
    return event


class AuditEntryFactory:
    """Creates the audit entry for each kind of action, with its level and its Activity event."""

    def call_service(
        self,
        user: User,
        call: ValidatedServiceCall,
        *,
        source: str,
        client: str | None,
        duration_ms: int,
    ) -> AuditEntry:
        """Return the entry of a successful `haac_bridge/call_service`."""
        return AuditEntry(
            "call_service",
            logging.INFO,
            (
                ("user", user_label(user)),
                ("source", source),
                ("client", client),
                ("entity", call.entity_id),
                ("service", call.service),
                ("data", call.data),
                ("result", "ok"),
                ("ms", duration_ms),
            ),
            activity=_activity(ACTION_CALL, "ok", call, client=client, source=source),
            context=call.context,
        )

    def call_failed(
        self, call: ValidatedServiceCall, client: str | None, source: str
    ) -> AuditEntry:
        """Return the Activity-only entry of a service call that failed; the wrapper logs the error."""
        return AuditEntry(
            "call_service",
            logging.WARNING,
            log=False,
            activity=_activity(ACTION_CALL, "failed", call, client=client, source=source),
            context=call.context,
        )

    def schedule_switched(
        self,
        schedule: Schedule,
        owner: User,
        call: ValidatedServiceCall,
        *,
        ok: bool,
        origin: RunOrigin,
    ) -> AuditEntry:
        """Return the entry of one entity switched by a schedule run; a failure is Activity-only."""
        return AuditEntry(
            "schedule_run",
            logging.INFO,
            (
                ("schedule", schedule.name),
                ("id", schedule.id[:8]),
                ("owner", user_label(owner)),
                ("trigger", "plan" if origin.triggered_by is None else "manual"),
                ("started_by", origin.triggered_by),
                ("client", origin.client),
                ("entity", call.entity_id),
                ("service", call.service),
                ("result", "ok"),
            ),
            log=ok,
            activity=_activity(
                ACTION_SCHEDULE, "ok" if ok else "failed", call, client=origin.client, source=None
            ),
            context=call.context,
        )

    def schedule_result(
        self, schedule: Schedule, result: str, done: int, total: int, *, removed: bool
    ) -> AuditEntry:
        """Return the entry of the result of a schedule run."""
        return AuditEntry(
            "schedule_result",
            logging.INFO,
            (
                ("schedule", schedule.name),
                ("id", schedule.id[:8]),
                ("owner", schedule.owner[:8]),
                ("result", result),
                ("entities", f"{done}/{total}"),
                ("removed", removed),
            ),
        )

    def schedule_not_run(self, schedule: Schedule, reason: str) -> AuditEntry:
        """Return the entry of a run that did not take place: missed, or the schedule was paused."""
        level = logging.WARNING if reason == "missed" else logging.INFO
        return AuditEntry(
            "schedule_not_run",
            level,
            (
                ("schedule", schedule.name),
                ("id", schedule.id[:8]),
                ("owner", schedule.owner[:8]),
                ("reason", reason),
            ),
            activity={"action": ACTION_SKIPPED, "result": "skipped"},
        )

    def schedule_changed(
        self, *, change: str, by: str, schedule: Schedule, details: dict[str, Any]
    ) -> AuditEntry:
        """Return the entry of a schedule that was created, changed, deleted, switched on or off.

        `by` is the label of the user, or `ha` when Home Assistant itself switched it.
        """
        return AuditEntry(
            "schedule_change",
            logging.INFO,
            (
                ("change", change),
                ("by", by),
                ("schedule", schedule.name),
                ("id", schedule.id[:8]),
                *details.items(),
            ),
        )

    def entity_disabled(
        self, *, user: User, entity_id: str, disabled: bool, schedules: int
    ) -> AuditEntry:
        """Return the entry of an entity a user deactivated or activated."""
        return AuditEntry(
            "entity_disabled" if disabled else "entity_enabled",
            logging.INFO,
            (("user", user_label(user)), ("entity", entity_id), ("schedules", schedules)),
        )

    def config_changed(self, *, what: str, **details: Any) -> AuditEntry:
        """Return the entry of a change of the configuration by an administrator or a reload."""
        return AuditEntry("config_change", logging.INFO, (("what", what), *details.items()))

    def startup(self, **details: Any) -> AuditEntry:
        """Return the entry written when the integration has started."""
        return AuditEntry("startup", logging.INFO, tuple(details.items()))

    def command(self, *, command_type: str, user_id: str | None, duration_ms: int) -> AuditEntry:
        """Return the debug entry of one `haac_bridge/*` command."""
        return AuditEntry(
            "command",
            logging.DEBUG,
            (("type", command_type), ("user", user_id), ("ms", duration_ms)),
        )

"""How a deactivated entity affects the schedules of its user: blocking, switching off and on (concept 7.5)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from ..core.errors import ErrorCode, ScheduleError
from ..schedules.model import OffReason, Schedule

if TYPE_CHECKING:
    from ..core.runtime import DisabledEntities


def blocked_by(disabled: DisabledEntities, schedule: Schedule) -> list[str]:
    """Return the entities of the schedule that its owner deactivated, in the order of the schedule."""
    deactivated = disabled.entities_of(schedule.owner)
    return [entity_id for entity_id in schedule.entities if entity_id in deactivated]


def require_unblocked(disabled: DisabledEntities, schedule: Schedule) -> None:
    """Raise HAB-SCH-008 if the schedule contains an entity its owner deactivated."""
    if blocked_by(disabled, schedule):
        raise ScheduleError(ErrorCode.SCH_BLOCKED)


def changes_for(
    disabled: DisabledEntities,
    schedules: list[Schedule],
    entity_id: str,
    now: datetime,
) -> tuple[list[Schedule], list[str]]:
    """Return the schedules to store after `entity_id` was deactivated or activated, and the ids switched.

    `schedules` are the owner's; `disabled` already holds the new state. Every schedule that contains
    the entity gets a new `updated_at`, so the revision changes and the app reads `blocked_by` again.
    A deactivation switches the enabled ones off with `off_reason`; an activation switches those with
    that reason on again unless another of their entities is still deactivated. A schedule the user
    switched off themselves (no `off_reason`) stays off.
    """
    replace: list[Schedule] = []
    switched: list[str] = []
    for schedule in schedules:
        if entity_id not in schedule.entities:
            continue
        updated = schedule.with_changes(updated_at=now)
        if schedule.enabled and blocked_by(disabled, schedule):
            updated = updated.with_changes(enabled=False, off_reason=OffReason.ENTITY_DISABLED)
        elif schedule.off_reason is OffReason.ENTITY_DISABLED and not blocked_by(
            disabled, schedule
        ):
            updated = updated.with_changes(enabled=True, off_reason=None)
        if updated.enabled != schedule.enabled:
            switched.append(schedule.id)
        replace.append(updated)
    return replace, switched

"""AuditEntry: one thing the bridge did, as a log line and optionally an Activity event (concept 21.3)."""

from dataclasses import dataclass
from typing import Any

from homeassistant.core import Context


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """What `AuditLog.record` writes: the log line (fields in order), and the Activity event if there is one.

    `log` is False for a failure that the command wrapper or the schedule runner already logs once.
    `context` ties the Activity event to the service call that caused it.
    """

    action: str
    level: int
    fields: tuple[tuple[str, Any], ...] = ()
    log: bool = True
    activity: dict[str, Any] | None = None
    context: Context | None = None

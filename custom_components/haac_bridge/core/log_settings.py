"""Log level and Activity switch as values; shared by the runtime data and the audit log (concept 21.2)."""

from dataclasses import dataclass, field
from enum import StrEnum
import logging

from ..const import DEFAULT_LOG_LEVEL


class LogLevel(StrEnum):
    """The log levels an administrator can choose."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def number(self) -> int:
        """Return the number of the level in the `logging` module."""
        return logging.getLevelNamesMapping()[self.name]


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """The log level and whether switching actions appear in the Activity page."""

    level: LogLevel = field(default=LogLevel(DEFAULT_LOG_LEVEL))
    activity: bool = True

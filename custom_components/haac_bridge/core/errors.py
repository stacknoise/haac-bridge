"""All HAB error codes and the exception hierarchy of HAAC Bridge (concept 18.3).

This is the only file that defines error codes. A new error gets the next free
number of its area; codes are never reused or renumbered. The attribute
docstring below each code is its technical description; `scripts/code_index.py`
reads it to generate `docs/error-codes.md`.
"""

from enum import StrEnum
from typing import Final

from homeassistant.exceptions import HomeAssistantError

from ..const import DOMAIN


class ErrorCode(StrEnum):
    """HAB error code; the value is the code, the lowercase name is the translation key."""

    CFG_INVALID = "HAB-CFG-001"
    """The haac_bridge section in configuration.yaml failed schema validation on reload."""

    CFG_UNKNOWN_USER = "HAB-CFG-002"
    """A `username` or `user_id` in the configuration matches no Home Assistant user."""

    AUTH_NO_USER = "HAB-AUTH-001"
    """The WebSocket connection has no Home Assistant user bound to its access token."""

    AUTH_INACTIVE = "HAB-AUTH-002"
    """The Home Assistant user bound to the connection is deactivated."""

    SVC_NOT_ALLOWED = "HAB-SVC-001"
    """The target entity is not exposed to the calling user."""

    SVC_NOT_AVAILABLE = "HAB-SVC-002"
    """The requested service does not belong to the domain of the target entity."""

    SVC_FAILED = "HAB-SVC-003"
    """Home Assistant raised an error while executing an allowed service call."""

    ENT_NOT_FOUND = "HAB-ENT-001"
    """The requested entity does not exist in the state machine."""

    HIST_UNAVAILABLE = "HAB-HIST-001"
    """Recorder or history is not loaded, or the query against it failed."""

    HIST_TOO_LONG = "HAB-HIST-002"
    """The requested history or statistics period is longer than the bridge allows."""

    SCH_INVALID = "HAB-SCH-001"
    """A schedule failed validation (name, time, days, action or entities)."""

    SCH_RUN_FAILED = "HAB-SCH-002"
    """A schedule run could not switch an entity (not exposed, unavailable or not permitted)."""

    SCH_NOT_FOUND = "HAB-SCH-003"
    """The schedule does not exist."""

    SCH_CONFLICT = "HAB-SCH-004"
    """The schedule changed after the caller loaded it (optimistic concurrency)."""

    SCH_LIMIT = "HAB-SCH-005"
    """The user already has the maximum number of schedules."""

    SCH_NOT_ALLOWED = "HAB-SCH-006"
    """A regular user touched a foreign schedule, or an admin tried to change a foreign entity list."""

    WS_INVALID_REQUEST = "HAB-WS-001"
    """The request fields of a haac_bridge/* command failed validation."""

    INT_UNEXPECTED = "HAB-INT-000"
    """An exception without a HAB code reached the command wrapper."""

    @property
    def translation_key(self) -> str:
        """Return the key of the user text in translations/en.json."""
        return self.name.lower()

    @property
    def area(self) -> str:
        """Return the area part of the code, e.g. `SVC` for `HAB-SVC-001`."""
        return self.value.split("-")[1]


APP_CODES: Final[dict[ErrorCode, str | None]] = {
    ErrorCode.CFG_INVALID: None,
    ErrorCode.CFG_UNKNOWN_USER: None,
    ErrorCode.AUTH_NO_USER: "HAAC-AUTH-003",
    ErrorCode.AUTH_INACTIVE: "HAAC-AUTH-006",
    ErrorCode.SVC_NOT_ALLOWED: "HAAC-BRG-003",
    ErrorCode.SVC_NOT_AVAILABLE: "HAAC-BRG-004",
    ErrorCode.SVC_FAILED: "HAAC-BRG-005",
    ErrorCode.ENT_NOT_FOUND: "HAAC-ENT-001",
    ErrorCode.HIST_UNAVAILABLE: "HAAC-BRG-006",
    ErrorCode.HIST_TOO_LONG: "HAAC-BRG-006",
    ErrorCode.SCH_INVALID: "HAAC-SCH-003",
    ErrorCode.SCH_RUN_FAILED: "HAAC-SCH-007",
    ErrorCode.SCH_NOT_FOUND: "HAAC-SCH-001",
    ErrorCode.SCH_CONFLICT: "HAAC-SCH-004",
    ErrorCode.SCH_LIMIT: "HAAC-SCH-005",
    ErrorCode.SCH_NOT_ALLOWED: "HAAC-SCH-006",
    ErrorCode.WS_INVALID_REQUEST: "HAAC-BRG-005",
    ErrorCode.INT_UNEXPECTED: "HAAC-BRG-005",
}
"""HAAC code the app shows for each HAB code (concept 18.3); None means admin only (Repairs)."""


class HaacBridgeError(HomeAssistantError):
    """Base of every exception raised by HAAC Bridge; carries an ErrorCode."""

    default_code: ErrorCode = ErrorCode.INT_UNEXPECTED

    def __init__(
        self,
        code: ErrorCode | None = None,
        placeholders: dict[str, str] | None = None,
    ) -> None:
        """Create the error with its code and optional translation placeholders."""
        self.code = code or self.default_code
        super().__init__(
            translation_domain=DOMAIN,
            translation_key=self.code.translation_key,
            translation_placeholders=placeholders,
        )


class ConfigError(HaacBridgeError):
    """Error in the haac_bridge YAML configuration (area CFG)."""

    default_code = ErrorCode.CFG_INVALID


class NotAllowedError(HaacBridgeError):
    """The caller could not be identified or is deactivated (area AUTH)."""

    default_code = ErrorCode.AUTH_NO_USER


class InvalidServiceError(HaacBridgeError):
    """A service call was rejected or failed (area SVC)."""

    default_code = ErrorCode.SVC_NOT_ALLOWED


class EntityNotFoundError(HaacBridgeError):
    """A requested entity does not exist (area ENT)."""

    default_code = ErrorCode.ENT_NOT_FOUND


class HistoryError(HaacBridgeError):
    """History or statistics could not be read (area HIST)."""

    default_code = ErrorCode.HIST_UNAVAILABLE


class ScheduleError(HaacBridgeError):
    """A schedule is invalid, missing, in conflict or not allowed (area SCH)."""

    default_code = ErrorCode.SCH_INVALID


class RequestError(HaacBridgeError):
    """A WebSocket request has an invalid format (area WS)."""

    default_code = ErrorCode.WS_INVALID_REQUEST


class InternalError(HaacBridgeError):
    """Unexpected error inside the bridge (area INT)."""

    default_code = ErrorCode.INT_UNEXPECTED

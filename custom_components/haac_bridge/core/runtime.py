"""Runtime data of HAAC Bridge stored in hass.data (concept 18.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey

from ..const import DOMAIN
from .error_factory import ErrorFactory
from .response_factory import ResponseFactory

if TYPE_CHECKING:
    from ..config.schema import UserEntry
    from ..entities.descriptor_factory import DescriptorFactory
    from ..exposure.exposure import Exposure
    from ..exposure.filter_factory import FilterFactory
    from ..schedules.manager import ScheduleManager
    from ..schedules.model import RunEntry
    from ..services.call_factory import ServiceCallFactory


class DisabledEntities(Protocol):
    """The entities each user deactivated (concept 7.5); the real store replaces the no-op one."""

    def is_disabled(self, user_id: str, entity_id: str) -> bool:
        """Return whether the user deactivated the entity."""

    def entities_of(self, user_id: str) -> dict[str, str]:
        """Return the user's deactivated entities with the ISO time of the deactivation."""


class RunLog(Protocol):
    """The log of schedule runs (concept 19.11); the real log replaces the no-op one."""

    def record(self, entry: RunEntry) -> None:
        """Append the entry of a finished or missed run."""


class NoDisabledEntities:
    """Stand-in until the store exists: nothing is deactivated."""

    def is_disabled(self, user_id: str, entity_id: str) -> bool:
        """Return False for every entity."""
        return False

    def entities_of(self, user_id: str) -> dict[str, str]:
        """Return no entities."""
        return {}


class NoRunLog:
    """Stand-in until the log exists: entries are dropped."""

    def record(self, entry: RunEntry) -> None:
        """Drop the entry."""


@dataclass(slots=True)
class HaacBridgeData:
    """Factories, current exposure and the user entries of YAML and UI; created in async_setup."""

    version: str
    filters: FilterFactory
    descriptors: DescriptorFactory
    services: ServiceCallFactory
    exposure: Exposure
    schedules: ScheduleManager
    errors: ErrorFactory = field(default_factory=ErrorFactory)
    responses: ResponseFactory = field(default_factory=ResponseFactory)
    disabled: DisabledEntities = field(default_factory=NoDisabledEntities)
    run_log: RunLog = field(default_factory=NoRunLog)
    issue_ids: set[str] = field(default_factory=set)
    yaml_entries: list[UserEntry] = field(default_factory=list)
    ui_entries: list[UserEntry] = field(default_factory=list)


DATA_KEY: HassKey[HaacBridgeData] = HassKey(DOMAIN)


def get_data(hass: HomeAssistant) -> HaacBridgeData:
    """Return the runtime data of HAAC Bridge."""
    return hass.data[DATA_KEY]

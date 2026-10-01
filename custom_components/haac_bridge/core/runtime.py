"""Runtime data of HAAC Bridge stored in hass.data (concept 18.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

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
    from ..services.call_factory import ServiceCallFactory


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
    issue_ids: set[str] = field(default_factory=set)
    yaml_entries: list[UserEntry] = field(default_factory=list)
    ui_entries: list[UserEntry] = field(default_factory=list)


DATA_KEY: HassKey[HaacBridgeData] = HassKey(DOMAIN)


def get_data(hass: HomeAssistant) -> HaacBridgeData:
    """Return the runtime data of HAAC Bridge."""
    return hass.data[DATA_KEY]

"""Switch platform: the `enabled` switch of every schedule (concept 19.5)."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .schedules.entities import PLATFORM_SWITCH
from .schedules.runtime import HaacBridgeConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: HaacBridgeConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the switches of the existing schedules and of those added later."""
    entry.runtime_data.async_setup_platform(PLATFORM_SWITCH, async_add_entities)

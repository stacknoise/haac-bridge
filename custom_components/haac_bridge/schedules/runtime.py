"""The typed config entry of HAAC Bridge: its runtime data is the schedule entity manager."""

from homeassistant.config_entries import ConfigEntry

from .entities import ScheduleEntityManager

HaacBridgeConfigEntry = ConfigEntry[ScheduleEntityManager]

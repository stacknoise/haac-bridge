"""The HA entities of a schedule: an `enabled` switch and a `next run` sensor (concept 19.5)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any

from homeassistant.auth import EVENT_USER_UPDATED
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN, SIGNAL_SCHEDULE_CHANGED, SIGNAL_SCHEDULES_CHANGED
from .manager import ScheduleManager
from .model import Schedule

PLATFORM_SWITCH = "switch"
PLATFORM_SENSOR = "sensor"
SUFFIX_ENABLED = "enabled"
SUFFIX_NEXT_RUN = "next_run"
UNIQUE_ID_PREFIX = f"{DOMAIN}_schedule_"

DEVICE_INFO = DeviceInfo(
    identifiers={(DOMAIN, "schedules")},
    name="HAAC Schedules",
    manufacturer="HAAC Bridge",
    entry_type=DeviceEntryType.SERVICE,
)
"""The one device all schedule entities belong to."""


def unique_id(schedule_id: str, suffix: str) -> str:
    """Return the unique id of a schedule entity, e.g. `haac_bridge_schedule_<id>_enabled`."""
    return f"{UNIQUE_ID_PREFIX}{schedule_id}_{suffix}"


def schedule_id_of(entity_unique_id: str) -> str | None:
    """Return the schedule id inside a unique id of this integration, or None if it has another form."""
    if not entity_unique_id.startswith(UNIQUE_ID_PREFIX):
        return None
    for suffix in (SUFFIX_ENABLED, SUFFIX_NEXT_RUN):
        if entity_unique_id.endswith(f"_{suffix}"):
            return entity_unique_id[len(UNIQUE_ID_PREFIX) : -len(suffix) - 1]
    return None


class ScheduleEntity(Entity):
    """Common part of the schedule entities: it follows the schedule in the store."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_device_info = DEVICE_INFO

    def __init__(self, manager: ScheduleManager, schedule_id: str, suffix: str) -> None:
        """Remember the schedule this entity shows and give it its unique id."""
        self._manager = manager
        self._schedule_id = schedule_id
        self._attr_unique_id = unique_id(schedule_id, suffix)
        self._owner_name: str | None = None

    @property
    def schedule(self) -> Schedule | None:
        """Return the schedule as it is stored now, or None if it was removed."""
        return self._manager.store.get(self._schedule_id)

    @property
    def available(self) -> bool:
        """Return True while the schedule exists."""
        return self.schedule is not None

    async def async_added_to_hass(self) -> None:
        """Refresh when this schedule changes, runs or is paused, and when its owner is renamed."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_SCHEDULE_CHANGED.format(self._schedule_id), self._handle_change
            )
        )
        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_USER_UPDATED, self._handle_owner_change, event_filter=self._is_owner_event
            )
        )

    async def async_update(self) -> None:
        """Look up the owner's name, which can only be read asynchronously; runs when added and on renames."""
        if (schedule := self.schedule) is None:
            return
        owner = await self.hass.auth.async_get_user(schedule.owner)
        self._owner_name = owner.name if owner else None

    @callback
    def _is_owner_event(self, event_data: Mapping[str, Any]) -> bool:
        """Return True for a user event about this schedule's owner."""
        schedule = self.schedule
        return schedule is not None and event_data.get("user_id") == schedule.owner

    @callback
    def _handle_owner_change(self, _event: Event) -> None:
        """Read the owner's name again after the owner changed."""
        self.async_schedule_update_ha_state(True)

    @property
    def _label(self) -> str | None:
        """Return the schedule name followed by its owner in brackets, so equal names stay apart."""
        schedule = self.schedule
        if schedule is None:
            return None
        return f"{schedule.name} ({self._owner_name})" if self._owner_name else schedule.name

    @callback
    def _handle_change(self) -> None:
        """Write the state after this schedule changed; a removed schedule's entity is being removed."""
        if self.schedule is None:
            return
        self.async_write_ha_state()


class ScheduleEnabledSwitch(ScheduleEntity, SwitchEntity):
    """Shows and sets whether the schedule is enabled; a system pause does not change it."""

    def __init__(self, manager: ScheduleManager, schedule_id: str) -> None:
        """Create the switch of one schedule."""
        super().__init__(manager, schedule_id, SUFFIX_ENABLED)

    @property
    def name(self) -> str | None:
        """Return the schedule name with its owner, which follows renames."""
        return self._label

    @property
    def is_on(self) -> bool | None:
        """Return whether the schedule is enabled."""
        schedule = self.schedule
        return schedule.enabled if schedule else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the schedule."""
        await self._manager.async_set_enabled(self._schedule_id, enabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the schedule."""
        await self._manager.async_set_enabled(self._schedule_id, enabled=False)


class ScheduleNextRunSensor(ScheduleEntity, SensorEntity):
    """Shows when the schedule runs next; unknown while it is disabled or paused."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, manager: ScheduleManager, schedule_id: str) -> None:
        """Create the sensor of one schedule."""
        super().__init__(manager, schedule_id, SUFFIX_NEXT_RUN)

    @property
    def name(self) -> str | None:
        """Return the schedule name with its owner, followed by `next run`."""
        label = self._label
        return f"{label} next run" if label else None

    @property
    def native_value(self) -> datetime | None:
        """Return the planned time of the next run."""
        return self._manager.planner.planned_run(self._schedule_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return owner, pause reason and last run."""
        schedule = self.schedule
        if schedule is None:
            return None
        last_run = schedule.last_run
        return {
            "owner": schedule.owner,
            "owner_name": self._owner_name,
            "paused_reason": schedule.paused.reason.value if schedule.paused else None,
            "last_run": None
            if last_run is None
            else {
                "at": last_run.at.isoformat(),
                "result": last_run.result.value,
                "code": last_run.code,
            },
        }


class ScheduleEntityManager:
    """Keeps one switch and one sensor per schedule in step with the store (concept 19.5)."""

    def __init__(self, hass: HomeAssistant, manager: ScheduleManager, entry: ConfigEntry) -> None:
        """Remember the manager and start following schedule changes until the entry unloads."""
        self._hass = hass
        self._manager = manager
        self._adders: dict[str, AddEntitiesCallback] = {}
        self._known: dict[str, set[str]] = {PLATFORM_SWITCH: set(), PLATFORM_SENSOR: set()}
        entry.async_on_unload(
            async_dispatcher_connect(hass, SIGNAL_SCHEDULES_CHANGED, self._async_sync)
        )

    @callback
    def async_setup_platform(self, platform: str, async_add_entities: AddEntitiesCallback) -> None:
        """Take over the add function of a platform and create the entities of all schedules."""
        self._adders[platform] = async_add_entities
        self._async_sync()

    @callback
    def async_sweep(self) -> None:
        """Remove registry entries whose schedule no longer exists (also after a missed removal)."""
        registry = er.async_get(self._hass)
        known = {schedule.id for schedule in self._manager.store.schedules}
        for entry in list(registry.entities.values()):
            if entry.platform != DOMAIN:
                continue
            schedule_id = schedule_id_of(entry.unique_id)
            if schedule_id is not None and schedule_id not in known:
                registry.async_remove(entry.entity_id)

    @callback
    def _async_sync(self) -> None:
        """Create the entities of new schedules and remove those of removed ones."""
        ids = {schedule.id for schedule in self._manager.store.schedules}
        builders: dict[str, Callable[[ScheduleManager, str], ScheduleEntity]] = {
            PLATFORM_SWITCH: ScheduleEnabledSwitch,
            PLATFORM_SENSOR: ScheduleNextRunSensor,
        }
        for platform, add in self._adders.items():
            known = self._known[platform]
            new = sorted(ids - known)
            if new:
                add([builders[platform](self._manager, schedule_id) for schedule_id in new], True)
                known.update(new)
        stale = {sid for known in self._known.values() for sid in known} - ids
        if stale:
            self._async_remove(stale)

    def _async_remove(self, schedule_ids: set[str]) -> None:
        """Remove the entities of removed schedules from the registry, which also removes their states."""
        registry = er.async_get(self._hass)
        for schedule_id in schedule_ids:
            for platform, suffix in (
                (PLATFORM_SWITCH, SUFFIX_ENABLED),
                (PLATFORM_SENSOR, SUFFIX_NEXT_RUN),
            ):
                entity_id = registry.async_get_entity_id(
                    platform, DOMAIN, unique_id(schedule_id, suffix)
                )
                if entity_id is not None:
                    registry.async_remove(entity_id)
                self._known[platform].discard(schedule_id)

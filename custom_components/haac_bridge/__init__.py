"""HAAC Bridge: per-user entity exposure for the HA Android Client (concept 10)."""

from homeassistant.auth import EVENT_USER_REMOVED, EVENT_USER_UPDATED
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import COMMANDS
from .config.repairs import async_check_users, async_report_invalid_config
from .config.schema import CONFIG_SCHEMA, parse_users
from .config.ui_users import parse_ui_users, users_of
from .const import CONF_USER_ID, CONF_USERS, DOMAIN, SERVICE_RELOAD, SIGNAL_EXPOSURE_CHANGED
from .core.command import async_register_commands
from .core.errors import ConfigError, ErrorCode
from .core.runtime import DATA_KEY, HaacBridgeData, get_data
from .entities.descriptor_factory import DescriptorFactory
from .exposure.exposure import Exposure
from .exposure.filter_factory import FilterFactory
from .exposure.own_entities import own_entity_checker
from .schedules.entities import ScheduleEntityManager
from .schedules.manager import ScheduleManager
from .schedules.runtime import HaacBridgeConfigEntry
from .services.call_factory import ServiceCallFactory

__all__ = ["CONFIG_SCHEMA", "DOMAIN"]

PLATFORMS = [Platform.SWITCH, Platform.SENSOR]
"""Platforms that carry the entities of the schedules (concept 19.5)."""


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Create the factories and exposure, register the commands and the reload action."""
    integration = await async_get_integration(hass, DOMAIN)
    filters = FilterFactory()
    entries = parse_users(config)
    data = HaacBridgeData(
        version=str(integration.version),
        filters=filters,
        descriptors=DescriptorFactory(hass),
        services=ServiceCallFactory(hass),
        exposure=Exposure(entries, filters, own_entity_checker(hass)),
        schedules=ScheduleManager(hass),
        yaml_entries=entries,
    )
    hass.data[DATA_KEY] = data
    await async_check_users(hass, data.issue_ids, entries)
    async_register_commands(hass, COMMANDS)
    await _async_start_schedules(hass, data.schedules)
    _async_listen_to_user_events(hass)
    if DOMAIN in config and not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_IMPORT}, data={})
        )

    async def _async_reload(call: ServiceCall) -> None:
        """Handle the haac_bridge.reload action."""
        await async_reload(hass)

    async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, _async_reload)
    return True


async def _async_start_schedules(hass: HomeAssistant, schedules: ScheduleManager) -> None:
    """Load the schedules, plan them once HA has started and cancel the timers when it stops."""
    await schedules.async_load()

    async def _start(_hass: HomeAssistant) -> None:
        """Plan every schedule once Home Assistant is running."""
        await schedules.async_start()

    async_at_started(hass, _start)

    @callback
    def _stop(_event: Event) -> None:
        """Cancel all schedule timers when Home Assistant stops."""
        schedules.async_stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop)


def _async_listen_to_user_events(hass: HomeAssistant) -> None:
    """Follow the deletion and the change of HA users with their schedules (concept 19.6)."""

    async def _removed(event: Event) -> None:
        """A HA user was deleted: delete their schedules and their UI entry."""
        await _async_user_removed(hass, event.data["user_id"])

    async def _updated(event: Event) -> None:
        """A HA user changed: pause their schedules if they are inactive, resume them otherwise."""
        await get_data(hass).schedules.async_sweep(event.data["user_id"])

    hass.bus.async_listen(EVENT_USER_REMOVED, _removed)
    hass.bus.async_listen(EVENT_USER_UPDATED, _updated)


async def _async_user_removed(hass: HomeAssistant, user_id: str) -> None:
    """Delete the schedules and the UI entry of a deleted HA user (concept 19.6.1).

    A YAML entry of that user cannot be edited; applying the configuration again reports it as HAB-CFG-002.
    """
    await get_data(hass).schedules.async_remove_owner(user_id)
    entry = next(iter(hass.config_entries.async_entries(DOMAIN)), None)
    records = users_of(entry.options) if entry else []
    if entry is None or not any(record[CONF_USER_ID] == user_id for record in records):
        await _async_apply(hass)
        return
    remaining = [record for record in records if record[CONF_USER_ID] != user_id]
    hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_USERS: remaining})


async def async_reload(hass: HomeAssistant) -> None:
    """Re-read the YAML configuration and rebuild the exposure of all users."""
    data = get_data(hass)
    config = await async_integration_yaml_config(hass, DOMAIN)
    if config is None:
        async_report_invalid_config(hass, data.issue_ids)
        raise ConfigError(ErrorCode.CFG_INVALID)
    data.yaml_entries = parse_users(config)
    await _async_apply(hass)


async def _async_apply(hass: HomeAssistant, *, sweep: bool = True) -> None:
    """Rebuild the exposure from the YAML and UI entries and tell connected apps.

    YAML entries come first, so a user who is configured in both places gets the YAML entry (concept 10.2).
    With `sweep`, schedules of users who are no longer configured are deleted (concept 19.6.3).
    """
    data = get_data(hass)
    entries = [*data.yaml_entries, *data.ui_entries]
    data.exposure = Exposure(entries, data.filters, own_entity_checker(hass))
    await async_check_users(hass, data.issue_ids, entries)
    if sweep:
        await data.schedules.async_sweep()
    async_dispatcher_send(hass, SIGNAL_EXPOSURE_CHANGED)


async def async_setup_entry(hass: HomeAssistant, entry: HaacBridgeConfigEntry) -> bool:
    """Take over the UI users, follow option changes and create the entities of the schedules."""
    data = get_data(hass)
    data.ui_entries = parse_ui_users(entry.options)
    await _async_apply(hass)
    data.schedules.users_ready = True
    entry.runtime_data = ScheduleEntityManager(hass, data.schedules, entry)
    entry.runtime_data.async_sweep()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply changed options of the entry without reloading the integration."""
    get_data(hass).ui_entries = parse_ui_users(entry.options)
    await _async_apply(hass)


async def async_unload_entry(hass: HomeAssistant, entry: HaacBridgeConfigEntry) -> bool:
    """Unload the schedule entities and drop the UI users; the YAML users stay."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    data = get_data(hass)
    data.schedules.users_ready = False
    data.ui_entries = []
    await _async_apply(hass, sweep=False)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete all schedules and their storage file when the entry is removed (concept 19.6)."""
    await get_data(hass).schedules.async_wipe()

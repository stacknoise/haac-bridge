"""HAAC Bridge: per-user entity exposure for the HA Android Client (concept 10)."""

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import COMMANDS
from .config.repairs import async_check_users, async_report_invalid_config
from .config.schema import CONFIG_SCHEMA, parse_users
from .const import DOMAIN, SERVICE_RELOAD
from .core.command import async_register_commands
from .core.errors import ConfigError, ErrorCode
from .core.runtime import DATA_KEY, HaacBridgeData, get_data
from .entities.descriptor_factory import DescriptorFactory
from .exposure.exposure import Exposure
from .exposure.filter_factory import FilterFactory

__all__ = ["CONFIG_SCHEMA", "DOMAIN"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Create the factories and exposure, register the commands and the reload action."""
    integration = await async_get_integration(hass, DOMAIN)
    filters = FilterFactory()
    entries = parse_users(config)
    data = HaacBridgeData(
        version=str(integration.version),
        filters=filters,
        descriptors=DescriptorFactory(hass),
        exposure=Exposure(entries, filters),
    )
    hass.data[DATA_KEY] = data
    await async_check_users(hass, data.issue_ids, entries)
    async_register_commands(hass, COMMANDS)

    async def _async_reload(call: ServiceCall) -> None:
        """Handle the haac_bridge.reload action."""
        await async_reload(hass)

    async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, _async_reload)
    return True


async def async_reload(hass: HomeAssistant) -> None:
    """Re-read the YAML configuration and rebuild the exposure of all users."""
    data = get_data(hass)
    config = await async_integration_yaml_config(hass, DOMAIN)
    if config is None:
        async_report_invalid_config(hass, data.issue_ids)
        raise ConfigError(ErrorCode.CFG_INVALID)
    entries = parse_users(config)
    data.exposure = Exposure(entries, data.filters)
    await async_check_users(hass, data.issue_ids, entries)
    # TODO(subscribe_entities): emit exposure_changed to connected apps (concept 10.2).

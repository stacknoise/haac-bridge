"""Instance ID and configured addresses of this Home Assistant instance (concept 4.3, 11.2)."""

from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import instance_id
from homeassistant.helpers.network import NoURLAvailableError, get_url


async def async_instance_identity(hass: HomeAssistant) -> dict[str, Any]:
    """Return the instance ID and the internal, external and cloud address (each `None` if unset)."""
    return {
        "instance_id": await instance_id.async_get(hass),
        "urls": {
            "internal": _url_or_none(
                lambda: get_url(hass, allow_external=False, allow_cloud=False, allow_ip=True)
            ),
            "external": _url_or_none(
                lambda: get_url(hass, allow_internal=False, allow_cloud=False, allow_ip=True)
            ),
            "cloud": _url_or_none(lambda: get_url(hass, require_cloud=True)),
        },
    }


def _url_or_none(resolve: Callable[[], str]) -> str | None:
    """Return the URL `resolve` finds, or `None` if Home Assistant has none of that kind."""
    try:
        return resolve()
    except NoURLAvailableError:
        return None

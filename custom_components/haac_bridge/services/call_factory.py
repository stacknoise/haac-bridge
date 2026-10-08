"""ServiceCallFactory: validated service calls for haac_bridge/call_service (concept 10.3, 11.4, 18.2)."""

import asyncio
from dataclasses import dataclass
from typing import Any

from homeassistant.auth.models import User
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Context, HomeAssistant, split_entity_id
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound, Unauthorized
import voluptuous as vol

from ..const import ALLOWED_SERVICES, SERVICE_TIMEOUT, TARGET_KEYS
from ..core.errors import EntityNotFoundError, ErrorCode, InvalidServiceError, RequestError
from ..exposure.exposure import Exposure


@dataclass(frozen=True, slots=True)
class ValidatedServiceCall:
    """A service call that passed all checks; the target is always exactly one entity."""

    domain: str
    service: str
    data: dict[str, Any]
    entity_id: str
    user_id: str


class ServiceCallFactory:
    """Creates service calls only for exposed entities and services of the entity's own domain."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Keep hass for state and service lookups."""
        self._hass = hass

    def create(
        self,
        exposure: Exposure,
        user: User,
        entity_id: str,
        service: str,
        data: dict[str, Any],
    ) -> ValidatedServiceCall:
        """Return the validated call or raise the matching HAB error (SVC-001, ENT-001, SVC-002, WS-001).

        Only services in ALLOWED_SERVICES are carried out, and only with their listed data keys.
        """
        if not exposure.is_exposed(user, entity_id):
            raise InvalidServiceError(ErrorCode.SVC_NOT_ALLOWED)
        if self._hass.states.get(entity_id) is None:
            raise EntityNotFoundError(ErrorCode.ENT_NOT_FOUND)
        domain = split_entity_id(entity_id)[0]
        allowed_keys = ALLOWED_SERVICES.get(domain, {}).get(service)
        if allowed_keys is None or not self._hass.services.has_service(domain, service):
            raise InvalidServiceError(ErrorCode.SVC_NOT_AVAILABLE)
        if TARGET_KEYS & data.keys() or not data.keys() <= allowed_keys:
            raise RequestError(ErrorCode.WS_INVALID_REQUEST)
        return ValidatedServiceCall(domain, service, dict(data), entity_id, user.id)


async def async_execute(hass: HomeAssistant, call: ValidatedServiceCall) -> None:
    """Run the call as the calling user, targeting only its entity; map HA errors to HAB codes.

    A call that takes longer than SERVICE_TIMEOUT seconds is given up and counts as failed, so a
    hanging integration never blocks the command or a schedule run (review finding U3).
    """
    try:
        async with asyncio.timeout(SERVICE_TIMEOUT):
            await hass.services.async_call(
                call.domain,
                call.service,
                call.data,
                blocking=True,
                context=Context(user_id=call.user_id),
                target={ATTR_ENTITY_ID: call.entity_id},
            )
    except TimeoutError as err:
        raise InvalidServiceError(ErrorCode.SVC_FAILED) from err
    except Unauthorized as err:
        raise InvalidServiceError(ErrorCode.SVC_NOT_ALLOWED) from err
    except ServiceNotFound as err:
        raise InvalidServiceError(ErrorCode.SVC_NOT_AVAILABLE) from err
    except (HomeAssistantError, vol.Invalid) as err:
        raise InvalidServiceError(ErrorCode.SVC_FAILED) from err

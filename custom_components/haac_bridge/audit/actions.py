"""The audited service call of `haac_bridge/call_service` (concept 21.3, 21.4)."""

from dataclasses import dataclass
import time
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant

from ..core.errors import ErrorCode, HaacBridgeError
from ..core.runtime import get_data
from ..services.call_factory import ValidatedServiceCall, async_execute


@dataclass(frozen=True, slots=True)
class ServiceRequest:
    """What a client asked for: the target, the service and its data, the device name and the source."""

    entity_id: str
    service: str
    service_data: dict[str, Any]
    source: str
    client: str | None = None


async def async_audited_call(hass: HomeAssistant, user: User, request: ServiceRequest) -> None:
    """Check and carry out a service call for the user, then record what happened.

    A success is one audit entry (log line and Activity event). A refusal or a failure is logged once by
    the command wrapper, which gets entity, service and device name from the error; only a failed
    service also reaches the Activity page, a refusal never does (concept 21.4).
    """
    data = get_data(hass)
    call: ValidatedServiceCall | None = None
    try:
        call = data.services.create(
            data.exposure, user, request.entity_id, request.service, request.service_data
        )
        started = time.monotonic()
        await async_execute(hass, call)
    except HaacBridgeError as err:
        err.with_details(entity=request.entity_id, service=request.service, client=request.client)
        if call is not None and err.code is ErrorCode.SVC_FAILED:
            data.audit.record(data.audit_entries.call_failed(call, request.client, request.source))
        raise
    duration_ms = round((time.monotonic() - started) * 1000)
    data.audit.record(
        data.audit_entries.call_service(
            user, call, source=request.source, client=request.client, duration_ms=duration_ms
        )
    )

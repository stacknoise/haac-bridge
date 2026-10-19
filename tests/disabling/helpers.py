"""Helpers shared by the deactivation tests; the command helpers are those of the schedule tests."""

from typing import Any

from ..schedules.test_api import CLIENT, create, error_code, ws

GARAGE = "switch.garage_socket"
FAN = "switch.office_fan"

__all__ = ["CLIENT", "FAN", "GARAGE", "create", "error_code", "set_disabled", "ws"]


async def set_disabled(client: Any, entity_id: str, *, disabled: bool = True) -> dict[str, Any]:
    """Deactivate or activate an entity and return the result; fail the test on an error."""
    reply = await ws(client, "entities/set_disabled", entity_id=entity_id, disabled=disabled)
    assert reply["success"], reply
    return reply["result"]

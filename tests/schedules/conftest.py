"""Shared fixtures and helpers for the schedule tests."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haac_bridge.schedules.model import Schedule, new_schedule

ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]
CREATED = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)


def utc(*args: int) -> datetime:
    """Return a UTC datetime."""
    return datetime(*args, tzinfo=UTC)


def make_schedule(
    when: dict[str, Any] | None = None,
    *,
    owner: str = "user-1",
    name: str = "Morning light",
    enabled: bool = True,
    created: datetime = CREATED,
    **changes: Any,
) -> Schedule:
    """Return a schedule for a fixed time (07:45 every day unless `when` is given)."""
    fields = {
        "name": name,
        "enabled": enabled,
        "when": when or {"type": "time", "time": "07:45", "days": ALL_DAYS},
        "action": "turn_on",
        "entities": ["switch.garage_socket"],
    }
    return new_schedule(owner, fields, created).with_changes(**changes)


@pytest.fixture(autouse=True)
def _mock_storage(hass_storage: dict[str, Any]) -> dict[str, Any]:
    """Keep the schedule store out of the real `.storage` directory."""
    return hass_storage


@pytest.fixture
async def berlin(hass: HomeAssistant) -> None:
    """Put HA into Berlin with its coordinates, for time zone and sun calculations."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    hass.config.latitude = 52.52
    hass.config.longitude = 13.405
    hass.config.elevation = 34


@dataclass(frozen=True)
class World:
    """The users of a test: two regular users, an admin and one the bridge does not know."""

    anton: User
    lena: User
    root: User
    bob: User


@pytest.fixture
async def world(
    add_user: Callable[..., User],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    demo_states: None,
) -> World:
    """Set up the bridge: anton and root see all switches, lena only the fan, bob is not configured."""
    anton = add_user("anton")
    lena = add_user("lena")
    root = add_user("root", admin=True)
    bob = add_user("bob")
    await setup_bridge(
        {
            "users": [
                {"user_id": anton.id, "filter": {"include_domains": ["switch"]}},
                {"user_id": lena.id, "filter": {"include_entities": ["switch.office_fan"]}},
                {"user_id": root.id, "filter": {"include_domains": ["switch"]}},
            ]
        }
    )
    return World(anton, lena, root, bob)

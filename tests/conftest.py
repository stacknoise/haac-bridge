"""Shared fixtures for HAAC Bridge tests."""

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.auth.models import Credentials, User
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import CLIENT_ID, MockUser

from custom_components.haac_bridge.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_setup(recorder_mock: Any, enable_custom_integrations: None) -> None:
    """Start the recorder before hass and allow loading custom integrations."""


@pytest.fixture
def add_user(hass: HomeAssistant) -> Callable[..., User]:
    """Return a helper that adds a HA user (not an admin unless `admin=True`) with a login name."""

    def _add(username: str, *, admin: bool = False) -> User:
        user = MockUser(name=username.title(), is_owner=admin)
        user.add_to_hass(hass)
        user.credentials.append(
            Credentials(
                auth_provider_type="homeassistant",
                auth_provider_id=None,
                data={"username": username},
            )
        )
        return user

    return _add


@pytest.fixture
def access_token_for(hass: HomeAssistant) -> Callable[[User], Coroutine[Any, Any, str]]:
    """Return a helper that creates an access token for a user."""

    async def _token(user: User) -> str:
        refresh_token = await hass.auth.async_create_refresh_token(user, CLIENT_ID)
        return hass.auth.async_create_access_token(refresh_token)

    return _token


@pytest.fixture
def client_for(
    hass: HomeAssistant,
    hass_ws_client: Callable[..., Coroutine[Any, Any, Any]],
    access_token_for: Callable[[User], Coroutine[Any, Any, str]],
) -> Callable[[User], Coroutine[Any, Any, Any]]:
    """Return a helper that opens a WebSocket client signed in as the given user."""

    async def _client(user: User) -> Any:
        return await hass_ws_client(hass, await access_token_for(user))

    return _client


@pytest.fixture
def setup_bridge(hass: HomeAssistant) -> Callable[[dict[str, Any]], Coroutine[Any, Any, None]]:
    """Return a helper that sets up haac_bridge with the given `haac_bridge:` section."""

    async def _setup(section: dict[str, Any]) -> None:
        assert await async_setup_component(hass, DOMAIN, {DOMAIN: section})
        await hass.async_block_till_done()

    return _setup


@pytest.fixture
def demo_states(hass: HomeAssistant) -> None:
    """Create states for supported and unsupported domains."""
    hass.states.async_set("switch.garage_socket", "on", {"device_class": "outlet"})
    hass.states.async_set("switch.office_fan", "off")
    hass.states.async_set(
        "sensor.living_room_temperature",
        "21.4",
        {"unit_of_measurement": "°C", "device_class": "temperature", "state_class": "measurement"},
    )
    hass.states.async_set("sensor.bath_humidity", "55", {"unit_of_measurement": "%"})
    hass.states.async_set(
        "climate.living_room",
        "heat",
        {"current_temperature": 21.4, "temperature": 22.0, "hvac_modes": ["off", "heat"]},
    )
    hass.states.async_set("climate.server_room", "cool")
    hass.states.async_set("light.kitchen", "on")

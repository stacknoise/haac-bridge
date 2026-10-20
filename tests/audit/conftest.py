"""Shared fixtures for the audit tests: a bridge with the log level `info` and an app login."""

from collections.abc import Callable, Coroutine, Iterator
import logging
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import Event, HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.haac_bridge.const import APP_CLIENT_ID, EVENT_ACTION, LOGGER_NAME

CLIENT = Callable[..., Coroutine[Any, Any, Any]]


@pytest.fixture(autouse=True)
def _reset_logger() -> Iterator[None]:
    """Give the next test an untouched package logger, because the bridge sets its level."""
    yield
    logging.getLogger(LOGGER_NAME).setLevel(logging.NOTSET)


@pytest.fixture(autouse=True)
def _mock_storage(hass_storage: dict[str, Any]) -> dict[str, Any]:
    """Keep the schedule store out of the real `.storage` directory."""
    return hass_storage


@pytest.fixture
def anton(add_user: Callable[..., User]) -> User:
    """Return a regular user."""
    return add_user("anton")


@pytest.fixture
def activity(hass: HomeAssistant) -> list[Event]:
    """Collect the `haac_bridge_action` events, which the Activity page shows."""
    return async_capture_events(hass, EVENT_ACTION)


@pytest.fixture
def setup_audited(
    anton: User,
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    demo_states: None,
) -> Callable[..., Coroutine[Any, Any, None]]:
    """Return a helper that sets up the bridge for anton, who may use the switches, with a `logging` block."""

    async def _setup(**logging_block: Any) -> None:
        await setup_bridge(
            {
                "users": [{"user_id": anton.id, "filter": {"include_domains": ["switch"]}}],
                "logging": {"level": "info", **logging_block},
            }
        )

    return _setup


@pytest.fixture
def app_client(hass: HomeAssistant, anton: User, hass_ws_client: CLIENT) -> CLIENT:
    """Return a helper that opens a WebSocket client as anton with the login of the HAAC app."""

    async def _client() -> Any:
        token = await hass.auth.async_create_refresh_token(anton, APP_CLIENT_ID)
        return await hass_ws_client(hass, hass.auth.async_create_access_token(token))

    return _client

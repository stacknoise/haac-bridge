"""Tests for resolving the caller of a WebSocket request (concept 10.3)."""

from types import SimpleNamespace
from typing import Any

from homeassistant.auth.models import User
import pytest

from custom_components.haac_bridge.core.caller import require_user
from custom_components.haac_bridge.core.errors import ErrorCode, NotAllowedError


def _connection(user: User | None) -> Any:
    """Return a stand-in for a WebSocket connection bound to `user`."""
    return SimpleNamespace(user=user)


def test_an_active_user_is_returned() -> None:
    user = User(name="Anton", perm_lookup=None, id="u1", is_active=True)  # type: ignore[arg-type]
    assert require_user(_connection(user)) is user


def test_a_missing_user_is_refused() -> None:
    with pytest.raises(NotAllowedError) as err:
        require_user(_connection(None))
    assert err.value.code is ErrorCode.AUTH_NO_USER


def test_a_deactivated_user_is_refused() -> None:
    user = User(name="Anton", perm_lookup=None, id="u1", is_active=False)  # type: ignore[arg-type]
    with pytest.raises(NotAllowedError) as err:
        require_user(_connection(user))
    assert err.value.code is ErrorCode.AUTH_INACTIVE

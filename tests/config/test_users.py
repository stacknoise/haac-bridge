"""Tests for matching entries to HA users and HAB-CFG-002 Repairs issues."""

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.haac_bridge.config.schema import UserEntry
from custom_components.haac_bridge.config.users import entry_matches


async def test_entry_matches_username_case_insensitive_and_user_id(
    add_user: Callable[[str], User],
) -> None:
    anton = add_user("anton")
    assert entry_matches(UserEntry(" Anton ", None, {}), anton)
    assert entry_matches(UserEntry(None, anton.id, {}), anton)
    assert not entry_matches(UserEntry("guest", None, {}), anton)
    assert not entry_matches(UserEntry(None, "other-id", {}), anton)


async def test_unknown_user_creates_repairs_issue(
    hass: HomeAssistant,
    issue_registry: ir.IssueRegistry,
    add_user: Callable[[str], User],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    add_user("anton")
    await setup_bridge({"users": [{"username": "anton"}, {"username": "nobody"}]})

    issues = [i for i in issue_registry.issues.values() if i.domain == "haac_bridge"]
    assert len(issues) == 1
    assert issues[0].translation_key == "cfg_unknown_user"
    assert issues[0].translation_placeholders == {"user": "nobody"}

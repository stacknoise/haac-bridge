"""Tests that the bridge's own entities are never exposed (concept 10.2, 19.5)."""

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haac_bridge.config.schema import UserEntry
from custom_components.haac_bridge.exposure.exposure import Exposure
from custom_components.haac_bridge.exposure.filter_factory import FilterFactory
from custom_components.haac_bridge.exposure.own_entities import own_entity_checker

ALL_SWITCHES = {"include_domains": ["switch"]}


def _user(user_id: str = "user-1") -> User:
    """Return a minimal HA user."""
    return User(name="Anton", perm_lookup=None, id=user_id)  # type: ignore[arg-type]


def _exposure(hass: HomeAssistant, user_id: str = "user-1") -> Exposure:
    """Return an exposure that shows all switches to the user, using the real entity registry."""
    entry = UserEntry(username=None, user_id=user_id, filter=_complete(ALL_SWITCHES))
    return Exposure([entry], FilterFactory(), own_entity_checker(hass))


def _complete(filter_: dict[str, list[str]]) -> dict[str, list[str]]:
    """Return a filter with all six keys, as the schema produces them."""
    keys = (
        "include_domains",
        "include_entities",
        "include_entity_globs",
        "exclude_domains",
        "exclude_entities",
        "exclude_entity_globs",
    )
    return {key: filter_.get(key, []) for key in keys}


def test_the_checker_knows_the_platform(hass: HomeAssistant) -> None:
    registry = er.async_get(hass)
    registry.async_get_or_create("switch", "haac_bridge", "a", suggested_object_id="own")
    registry.async_get_or_create("switch", "other", "b", suggested_object_id="foreign")
    check = own_entity_checker(hass)
    assert check("switch.own") is True
    assert check("switch.foreign") is False
    assert check("switch.unregistered") is False


def test_own_entities_are_never_exposed(hass: HomeAssistant) -> None:
    registry = er.async_get(hass)
    registry.async_get_or_create("switch", "haac_bridge", "a", suggested_object_id="own")
    hass.states.async_set("switch.own", "on")
    hass.states.async_set("switch.garage_socket", "on")
    exposure = _exposure(hass)
    user = _user()

    assert exposure.is_exposed(user, "switch.garage_socket")
    assert not exposure.is_exposed(user, "switch.own")
    assert exposure.exposed_entity_ids(hass, user) == ["switch.garage_socket"]
    assert exposure.filter_exposed(user, ["switch.own", "switch.garage_socket"]) == [
        "switch.garage_socket"
    ]
    assert exposure.snapshot(hass, user).entity_ids == ["switch.garage_socket"]


def test_is_configured(hass: HomeAssistant) -> None:
    exposure = _exposure(hass)
    assert exposure.is_configured(_user())
    assert not exposure.is_configured(_user("someone-else"))


async def test_deleted_own_entities_stay_hidden(hass: HomeAssistant) -> None:
    registry = er.async_get(hass)
    registry.async_get_or_create("switch", "haac_bridge", "a", suggested_object_id="own")
    registry.async_get_or_create("switch", "other", "b", suggested_object_id="foreign")
    check = own_entity_checker(hass)
    assert check("switch.own") is True

    registry.async_remove("switch.own")
    registry.async_remove("switch.foreign")
    await hass.async_block_till_done()

    assert check("switch.own") is True
    assert check("switch.foreign") is False
    exposure = _exposure(hass)
    assert exposure.filter_exposed(_user(), ["switch.own", "switch.foreign"]) == ["switch.foreign"]


async def test_a_restored_foreign_entity_with_an_old_own_id_is_not_hidden(
    hass: HomeAssistant,
) -> None:
    registry = er.async_get(hass)
    registry.async_get_or_create("switch", "haac_bridge", "a", suggested_object_id="reused")
    check = own_entity_checker(hass)
    registry.async_remove("switch.reused")
    await hass.async_block_till_done()
    assert check("switch.reused") is True

    registry.async_get_or_create("switch", "other", "b", suggested_object_id="reused")
    await hass.async_block_till_done()

    assert check("switch.reused") is False

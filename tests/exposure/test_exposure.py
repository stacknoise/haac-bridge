"""Tests for per-user filter evaluation, deny by default and the revision (concept 10.2, 14.2)."""

from collections.abc import Callable

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
import pytest

from custom_components.haac_bridge.config.schema import CONFIG_SCHEMA, parse_users
from custom_components.haac_bridge.exposure.exposure import Exposure, compute_revision
from custom_components.haac_bridge.exposure.filter_factory import FilterFactory

YAML = {
    "haac_bridge": {
        "users": [
            {
                "username": "anton",
                "filter": {
                    "include_domains": ["climate", "light"],
                    "include_entities": ["switch.garage_socket", "sensor.living_room_temperature"],
                    "include_entity_globs": ["sensor.*_humidity"],
                    "exclude_entities": ["climate.server_room"],
                },
            },
            {"username": "guest", "filter": {"include_entities": ["switch.office_fan"]}},
            {"username": "excludes_only", "filter": {"exclude_domains": ["light"]}},
        ]
    }
}


@pytest.fixture
def exposure() -> Exposure:
    """Return the exposure built from YAML."""
    return Exposure(parse_users(CONFIG_SCHEMA(YAML)), FilterFactory())


@pytest.mark.usefixtures("demo_states")
async def test_filter_per_user(
    hass: HomeAssistant, exposure: Exposure, add_user: Callable[[str], User]
) -> None:
    anton, guest = add_user("anton"), add_user("guest")
    assert exposure.exposed_entity_ids(hass, anton) == [
        "climate.living_room",
        "sensor.bath_humidity",
        "sensor.living_room_temperature",
        "switch.garage_socket",
    ]
    assert exposure.exposed_entity_ids(hass, guest) == ["switch.office_fan"]


@pytest.mark.usefixtures("demo_states")
async def test_only_v1_domains_and_exclude_beats_include(
    hass: HomeAssistant, exposure: Exposure, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    assert not exposure.is_exposed(anton, "light.kitchen")
    assert not exposure.is_exposed(anton, "climate.server_room")
    assert exposure.is_exposed(anton, "climate.living_room")


@pytest.mark.usefixtures("demo_states")
async def test_deny_by_default(
    hass: HomeAssistant, exposure: Exposure, add_user: Callable[[str], User]
) -> None:
    stranger, excludes_only = add_user("stranger"), add_user("excludes_only")
    assert exposure.exposed_entity_ids(hass, stranger) == []
    assert not exposure.is_exposed(stranger, "switch.garage_socket")
    assert exposure.exposed_entity_ids(hass, excludes_only) == []


@pytest.mark.usefixtures("demo_states")
async def test_new_entity_matching_glob_changes_revision(
    hass: HomeAssistant, exposure: Exposure, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    before = exposure.snapshot(hass, anton)
    hass.states.async_set("sensor.cellar_humidity", "70")
    after = exposure.snapshot(hass, anton)
    assert "sensor.cellar_humidity" in after.entity_ids
    assert after.revision != before.revision

    hass.states.async_remove("sensor.cellar_humidity")
    assert exposure.snapshot(hass, anton).revision == before.revision


async def test_revision_is_order_independent() -> None:
    assert compute_revision(["b.x", "a.y"]) == compute_revision(["a.y", "b.x"])
    assert compute_revision([]) != compute_revision(["a.y"])

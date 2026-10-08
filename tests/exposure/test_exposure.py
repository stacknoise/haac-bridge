"""Tests for per-user filter evaluation, deny by default and the revision (concept 10.2, 14.2)."""

from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.haac_bridge.config.schema import CONFIG_SCHEMA, parse_users
from custom_components.haac_bridge.config.users import entry_matches
from custom_components.haac_bridge.core.runtime import get_data
from custom_components.haac_bridge.exposure.exposure import (
    CACHE_LIMIT,
    Exposure,
    compute_revision,
)
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
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    anton = add_user("anton")
    await setup_bridge(YAML["haac_bridge"])
    before = get_data(hass).exposure.snapshot(hass, anton)
    hass.states.async_set("sensor.cellar_humidity", "70")
    after = get_data(hass).exposure.snapshot(hass, anton)
    assert "sensor.cellar_humidity" in after.entity_ids
    assert after.revision != before.revision

    hass.states.async_remove("sensor.cellar_humidity")
    assert get_data(hass).exposure.snapshot(hass, anton).revision == before.revision


@pytest.mark.usefixtures("demo_states")
async def test_answers_are_cached_per_user_and_entity(
    hass: HomeAssistant, exposure: Exposure, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    module = "custom_components.haac_bridge.exposure.exposure"
    with patch(f"{module}.entry_matches", wraps=entry_matches) as matches:
        for _ in range(3):
            assert exposure.is_exposed(anton, "switch.garage_socket")
            first = exposure.exposed_entity_ids(hass, anton)
            first.clear()  # callers get a copy, never the cached list
    assert matches.call_count == 1  # anton is the first entry: one lookup for all calls
    assert exposure._decisions == {(anton.id, "switch.garage_socket"): True}
    assert exposure._exposed_sets[anton.id] == exposure.exposed_entity_ids(hass, anton) != []


@pytest.mark.usefixtures("demo_states")
async def test_a_login_name_added_later_is_picked_up(
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    await setup_bridge(YAML["haac_bridge"])
    guest = add_user("someone")
    exposure = get_data(hass).exposure
    assert not exposure.is_exposed(guest, "switch.office_fan")

    guest.credentials[0].data["username"] = "guest"
    await hass.auth.async_update_user(guest, name="Guest")
    await hass.async_block_till_done()

    assert get_data(hass).exposure.is_exposed(guest, "switch.office_fan")


@pytest.mark.usefixtures("demo_states")
async def test_an_entity_taken_over_by_the_bridge_is_hidden_at_once(
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> None:
    anton = add_user("anton")
    await setup_bridge(YAML["haac_bridge"])
    exposure = get_data(hass).exposure
    assert exposure.is_exposed(anton, "sensor.attic_humidity")  # cached as exposed

    entry = er.async_get(hass).async_get_or_create(
        "sensor", "haac_bridge", "x", suggested_object_id="attic_humidity"
    )
    await hass.async_block_till_done()
    assert entry.entity_id == "sensor.attic_humidity"
    hass.states.async_set("sensor.attic_humidity", "40")

    assert not exposure.is_exposed(anton, "sensor.attic_humidity")
    assert "sensor.attic_humidity" not in exposure.exposed_entity_ids(hass, anton)


async def test_the_decision_cache_is_bounded(hass: HomeAssistant) -> None:
    exposure = Exposure(parse_users(CONFIG_SCHEMA(YAML)), FilterFactory())
    user = User(name="Anton", perm_lookup=None, id="u1")  # type: ignore[arg-type]
    for i in range(CACHE_LIMIT + 5):
        exposure.is_exposed(user, f"sensor.s{i}")
    assert len(exposure._decisions) <= CACHE_LIMIT


async def test_revision_is_order_independent() -> None:
    assert compute_revision(["b.x", "a.y"]) == compute_revision(["a.y", "b.x"])
    assert compute_revision([]) != compute_revision(["a.y"])


async def test_revision_covers_configured_names_of_exposed_entities() -> None:
    bare = compute_revision(["a.y"])
    assert compute_revision(["a.y"], {}) == bare
    assert compute_revision(["a.y"], {"b.x": "Other"}) == bare
    assert compute_revision(["a.y"], {"a.y": "One"}) != bare
    assert compute_revision(["a.y"], {"a.y": "One"}) != compute_revision(["a.y"], {"a.y": "Two"})


@pytest.mark.usefixtures("demo_states")
async def test_snapshot_holds_names_of_exposed_entities_only(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    yaml = {
        "haac_bridge": {
            "entity_config": {
                "switch.garage_socket": {"name": "Garage"},
                "switch.office_fan": {"name": "Fan"},
            },
            "users": [
                {"username": "anton", "filter": {"include_entities": ["switch.garage_socket"]}}
            ],
        }
    }
    anton = add_user("anton")
    snapshot = Exposure(parse_users(CONFIG_SCHEMA(yaml)), FilterFactory()).snapshot(hass, anton)
    assert snapshot.names == {"switch.garage_socket": "Garage"}
    assert snapshot.revision == compute_revision(
        ["switch.garage_socket"], {"switch.garage_socket": "Garage"}
    )


def test_an_unsupported_domain_is_rejected_before_the_user_rule_is_looked_up() -> None:
    exposure = Exposure([], FilterFactory())
    user = User(name="Anton", perm_lookup=None, id="user-1")  # type: ignore[arg-type]
    with patch.object(Exposure, "_rule_for", side_effect=AssertionError) as rule_for:
        assert not exposure.is_exposed(user, "light.kitchen")
    rule_for.assert_not_called()

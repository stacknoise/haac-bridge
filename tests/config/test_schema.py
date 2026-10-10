"""Tests for the YAML schema (concept 10.2)."""

import pytest
import voluptuous as vol

from custom_components.haac_bridge.config.schema import CONFIG_SCHEMA, parse_users


async def test_valid_config_is_parsed() -> None:
    config = CONFIG_SCHEMA(
        {
            "haac_bridge": {
                "users": [
                    {
                        "username": "anton",
                        "filter": {
                            "include_domains": "climate",
                            "include_entity_globs": ["sensor.*_humidity"],
                            "exclude_entities": ["climate.server_room"],
                        },
                    },
                    {"user_id": "abc123"},
                ]
            }
        }
    )
    anton, other = parse_users(config)
    assert anton.username == "anton"
    assert anton.filter["include_domains"] == ["climate"]
    assert anton.filter["include_entities"] == []
    assert other.user_id == "abc123"
    assert other.filter["include_domains"] == []


async def test_entity_names_global_and_per_user() -> None:
    config = CONFIG_SCHEMA(
        {
            "haac_bridge": {
                "entity_config": {
                    "sensor.outdoor_temperature": {"name": " Outside "},
                    "switch.garage_socket": {"name": "Garage"},
                    "sensor.bath_humidity": {},
                },
                "users": [
                    {"username": "anton"},
                    {
                        "username": "guest",
                        "entity_config": {"sensor.outdoor_temperature": {"name": "Temperature"}},
                    },
                ],
            }
        }
    )
    anton, guest = parse_users(config)
    assert anton.names == {
        "sensor.outdoor_temperature": "Outside",
        "switch.garage_socket": "Garage",
    }
    assert guest.names == {
        "sensor.outdoor_temperature": "Temperature",
        "switch.garage_socket": "Garage",
    }


@pytest.mark.parametrize(
    "entity_config",
    [
        {"not an entity id": {"name": "X"}},
        {"sensor.a": {"name": "  "}},
        {"sensor.a": {"icon": "mdi:x"}},
    ],
)
async def test_invalid_entity_config_is_rejected(entity_config: dict) -> None:
    with pytest.raises(vol.Invalid):
        CONFIG_SCHEMA({"haac_bridge": {"entity_config": entity_config}})
    with pytest.raises(vol.Invalid):
        CONFIG_SCHEMA(
            {"haac_bridge": {"users": [{"username": "anton", "entity_config": entity_config}]}}
        )


async def test_missing_section_means_no_users() -> None:
    assert parse_users(CONFIG_SCHEMA({})) == []
    assert parse_users(CONFIG_SCHEMA({"haac_bridge": {}})) == []


async def test_bare_section_means_no_users() -> None:
    """A `haac_bridge:` line without content is read as None and means no users, not an invalid config."""
    assert parse_users(CONFIG_SCHEMA({"haac_bridge": None})) == []


@pytest.mark.parametrize(
    "user",
    [
        {"filter": {"include_domains": ["switch"]}},
        {"username": "anton", "user_id": "abc123"},
        {"username": "anton", "filter": {"include_entities": ["not an entity id"]}},
        {"username": "anton", "unknown_key": True},
    ],
)
async def test_invalid_user_entries_are_rejected(user: dict) -> None:
    with pytest.raises(vol.Invalid):
        CONFIG_SCHEMA({"haac_bridge": {"users": [user]}})


@pytest.mark.parametrize("glob", ["*_humidity", "sensor.", ".x", " "])
async def test_wildcards_must_look_like_domain_dot_pattern(glob: str) -> None:
    for key in ("include_entity_globs", "exclude_entity_globs"):
        with pytest.raises(vol.Invalid):
            CONFIG_SCHEMA(
                {
                    "haac_bridge": {
                        "users": [{"username": "anton", "filter": {key: [glob]}}],
                    }
                }
            )


async def test_valid_wildcards_pass() -> None:
    config = CONFIG_SCHEMA(
        {
            "haac_bridge": {
                "users": [
                    {
                        "username": "anton",
                        "filter": {
                            "include_entity_globs": ["sensor.*_humidity", "switch.*"],
                            "exclude_entity_globs": ["*.test_*"],
                        },
                    }
                ]
            }
        }
    )
    assert parse_users(config)[0].filter["include_entity_globs"] == [
        "sensor.*_humidity",
        "switch.*",
    ]

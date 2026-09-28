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


async def test_missing_section_means_no_users() -> None:
    assert parse_users(CONFIG_SCHEMA({})) == []
    assert parse_users(CONFIG_SCHEMA({"haac_bridge": {}})) == []


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

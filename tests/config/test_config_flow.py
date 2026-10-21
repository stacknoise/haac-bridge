"""Tests for the config flow and the options flow (concept 10.2)."""

from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from homeassistant.auth.models import User
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haac_bridge.config.ui_yaml import export_users, import_users
from custom_components.haac_bridge.const import DOMAIN
from custom_components.haac_bridge.core.runtime import get_data

SetupBridge = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


async def _add_entry(hass: HomeAssistant, options: dict[str, Any] | None = None) -> MockConfigEntry:
    """Add and set up a config entry with the given options."""
    entry = MockConfigEntry(domain=DOMAIN, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _menu(hass: HomeAssistant, entry: MockConfigEntry, step: str) -> dict[str, Any]:
    """Open the options flow and choose a menu entry."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step}
    )


async def test_config_flow_creates_one_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HAAC Bridge"

    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert again["type"] is FlowResultType.ABORT
    assert again["reason"] == "single_instance_allowed"


async def test_add_user_with_names(hass: HomeAssistant, add_user: Callable[[str], User]) -> None:
    anton = add_user("anton")
    entry = await _add_entry(hass)

    result = await _menu(hass, entry, "add_user")
    assert result["step_id"] == "add_user"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": anton.id}
    )
    assert result["step_id"] == "filter"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "include_entities": ["switch.garage_socket"],
            "include_entity_globs": ["sensor.*_humidity"],
            "exclude_entities": ["sensor.bath_humidity"],
        },
    )
    assert result["step_id"] == "names"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"switch.garage_socket": " Garage "}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "users": [
            {
                "user_id": anton.id,
                "filter": {
                    "include_entities": ["switch.garage_socket"],
                    "include_entity_globs": ["sensor.*_humidity"],
                    "exclude_entities": ["sensor.bath_humidity"],
                },
                "names": {"switch.garage_socket": "Garage"},
            }
        ]
    }
    exposure = get_data(hass).exposure
    assert exposure.is_exposed(anton, "switch.garage_socket")
    assert exposure.is_exposed(anton, "sensor.kitchen_humidity")
    assert not exposure.is_exposed(anton, "sensor.bath_humidity")
    assert exposure.configured_names(anton) == {"switch.garage_socket": "Garage"}


async def test_filter_needs_an_include_rule_and_valid_wildcards(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    entry = await _add_entry(hass)
    result = await _menu(hass, entry, "add_user")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": anton.id}
    )

    only_exclude = await hass.config_entries.options.async_configure(
        result["flow_id"], {"exclude_domains": ["climate"]}
    )
    assert only_exclude["step_id"] == "filter"
    assert only_exclude["errors"] == {"base": "no_include"}

    bad_glob = await hass.config_entries.options.async_configure(
        result["flow_id"], {"include_entity_globs": ["humidity"]}
    )
    assert bad_glob["errors"] == {"base": "invalid_glob"}

    done = await hass.config_entries.options.async_configure(
        result["flow_id"], {"include_domains": ["climate"]}
    )
    assert done["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["users"][0]["filter"] == {"include_domains": ["climate"]}


async def test_change_and_remove_a_user(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    entry = await _add_entry(
        hass,
        {
            "users": [
                {
                    "user_id": anton.id,
                    "filter": {"include_entities": ["switch.garage_socket"]},
                    "names": {"switch.garage_socket": "Garage"},
                }
            ]
        },
    )
    assert get_data(hass).exposure.is_exposed(anton, "switch.garage_socket")

    result = await _menu(hass, entry, "edit_user")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": anton.id}
    )
    assert result["step_id"] == "filter"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"include_domains": ["sensor"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["users"] == [
        {"user_id": anton.id, "filter": {"include_domains": ["sensor"]}, "names": {}}
    ]
    assert not get_data(hass).exposure.is_exposed(anton, "switch.garage_socket")
    assert get_data(hass).exposure.is_exposed(anton, "sensor.living_room_temperature")

    result = await _menu(hass, entry, "remove_user")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": anton.id}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"users": []}
    assert not get_data(hass).exposure.is_exposed(anton, "sensor.living_room_temperature")


async def test_yaml_wins_over_the_ui_for_the_same_user(
    hass: HomeAssistant, add_user: Callable[[str], User], setup_bridge: SetupBridge
) -> None:
    anton = add_user("anton")
    await setup_bridge(
        {"users": [{"username": "anton", "filter": {"include_entities": ["sensor.outdoor"]}}]}
    )
    await _add_entry(
        hass,
        {
            "users": [
                {"user_id": anton.id, "filter": {"include_entities": ["switch.garage_socket"]}}
            ]
        },
    )

    exposure = get_data(hass).exposure
    assert exposure.is_exposed(anton, "sensor.outdoor")
    assert not exposure.is_exposed(anton, "switch.garage_socket")


async def test_unloading_the_entry_drops_the_ui_users(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    entry = await _add_entry(
        hass,
        {
            "users": [
                {"user_id": anton.id, "filter": {"include_entities": ["switch.garage_socket"]}}
            ]
        },
    )
    assert get_data(hass).exposure.is_exposed(anton, "switch.garage_socket")

    assert await hass.config_entries.async_unload(entry.entry_id)

    assert not get_data(hass).exposure.is_exposed(anton, "switch.garage_socket")


@pytest.mark.parametrize("configured", [False, True])
async def test_menu_offers_only_possible_entries(
    hass: HomeAssistant, add_user: Callable[[str], User], configured: bool
) -> None:
    anton = add_user("anton")
    options = {"users": [{"user_id": anton.id, "filter": {"include_domains": ["sensor"]}}]}
    entry = await _add_entry(hass, options if configured else {})

    result = await hass.config_entries.options.async_init(entry.entry_id)

    expected = (
        ["edit_user", "remove_user", "export_yaml", "import_yaml", "logging"]
        if configured
        else ["add_user", "import_yaml", "logging"]
    )
    assert result["menu_options"] == expected


async def test_export_shows_the_ui_users_as_yaml(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    options = {
        "users": [
            {
                "user_id": anton.id,
                "filter": {"include_entities": ["sensor.humidity"]},
                "names": {"sensor.humidity": "Humidity"},
            }
        ]
    }
    entry = await _add_entry(hass, options)

    result = await _menu(hass, entry, "export_yaml")

    assert result["step_id"] == "export_yaml"
    exported = result["description_placeholders"]["yaml"]
    assert "haac_bridge:" in exported
    assert anton.id in exported
    assert "sensor.humidity" in exported
    assert "name: Humidity" in exported
    # Confirming leaves everything as it was and returns to the menu.
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.MENU
    assert entry.options == options


async def test_import_adds_and_replaces_users(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    maria = add_user("maria")
    old = {"user_id": anton.id, "filter": {"include_domains": ["sensor"]}}
    entry = await _add_entry(hass, {"users": [old]})
    text = (
        "haac_bridge:\n"
        "  users:\n"
        f"    - user_id: {anton.id}\n"
        "      filter:\n"
        "        include_entities: [sensor.humidity]\n"
        "      entity_config:\n"
        "        sensor.humidity:\n"
        "          name: Humidity\n"
        f"    - user_id: {maria.id}\n"
        "      filter:\n"
        "        include_domains: [switch]\n"
    )

    result = await _menu(hass, entry, "import_yaml")
    assert result["step_id"] == "import_yaml"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"yaml": text})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    users = {record["user_id"]: record for record in entry.options["users"]}
    assert users[anton.id]["filter"] == {"include_entities": ["sensor.humidity"]}
    assert users[anton.id]["names"] == {"sensor.humidity": "Humidity"}
    assert users[maria.id]["filter"] == {"include_domains": ["switch"]}
    assert get_data(hass).exposure.is_exposed(anton, "sensor.humidity")


async def _user_choices(hass: HomeAssistant, entry: MockConfigEntry, step: str) -> list[str]:
    """Open a user form of the options flow and return the offered user ids."""
    result = await _menu(hass, entry, step)
    options = result["data_schema"].schema["user_id"].config["options"]
    return [option["value"] for option in options]


async def test_a_deactivated_user_can_still_be_changed_and_removed(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    entry = await _add_entry(
        hass, {"users": [{"user_id": anton.id, "filter": {"include_domains": ["sensor"]}}]}
    )
    await hass.auth.async_deactivate_user(anton)

    assert await _user_choices(hass, entry, "edit_user") == [anton.id]
    result = await _menu(hass, entry, "remove_user")
    options = result["data_schema"].schema["user_id"].config["options"]
    assert options[0]["label"] == "Anton (deactivated)"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": anton.id}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"users": []}


async def test_a_deactivated_user_is_not_offered_to_add(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    lena = add_user("lena")
    await hass.auth.async_deactivate_user(lena)
    entry = await _add_entry(hass)

    assert await _user_choices(hass, entry, "add_user") == [anton.id]


async def test_import_accepts_a_configured_user_who_is_deactivated_now(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    entry = await _add_entry(
        hass, {"users": [{"user_id": anton.id, "filter": {"include_domains": ["sensor"]}}]}
    )
    await hass.auth.async_deactivate_user(anton)
    text = f"users:\n  - user_id: {anton.id}\n    filter:\n      include_domains: [switch]\n"

    result = await _menu(hass, entry, "import_yaml")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"yaml": text})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["users"][0]["filter"] == {"include_domains": ["switch"]}


@pytest.mark.parametrize("kind", ["deactivated", "system"])
async def test_import_rejects_users_the_form_never_offers(
    hass: HomeAssistant, add_user: Callable[[str], User], kind: str
) -> None:
    if kind == "system":
        user = await hass.auth.async_create_system_user("Supervisor")
    else:
        user = add_user("lena")
        await hass.auth.async_deactivate_user(user)
    entry = await _add_entry(hass)
    text = f"users:\n  - user_id: {user.id}\n    filter:\n      include_domains: [sensor]\n"

    result = await _menu(hass, entry, "import_yaml")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"yaml": text})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown_user"}
    assert entry.options == {}


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("users: [", "invalid_yaml"),
        ("just a sentence", "invalid_yaml"),
        ("users:\n  - user_id: !secret token\n", "invalid_yaml"),
        ("users:\n  - user_id: abc\n    unknown_key: true\n", "invalid_config"),
        ("users: []\n", "no_users"),
        (
            "users:\n  - user_id: abc\n    filter:\n      include_entity_globs: ['*_humidity']\n",
            "invalid_config",
        ),
        (
            "users:\n  - username: anton\n    filter:\n      include_domains: [sensor]\n",
            "needs_user_id",
        ),
        ("users:\n  - user_id: abc\n", "no_include"),
        (
            "users:\n  - user_id: not-a-ha-user\n    filter:\n      include_domains: [sensor]\n",
            "unknown_user",
        ),
    ],
)
async def test_import_rejects_unusable_yaml(hass: HomeAssistant, text: str, error: str) -> None:
    entry = await _add_entry(hass)

    result = await _menu(hass, entry, "import_yaml")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"yaml": text})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert entry.options == {}


def test_an_export_imports_back_unchanged() -> None:
    options = {
        "users": [
            {
                "user_id": "abc",
                "filter": {
                    "include_entities": ["sensor.humidity"],
                    "exclude_entity_globs": ["sensor.*_raw"],
                },
                "names": {"sensor.humidity": "Humidity: inside"},
            }
        ]
    }

    records, error = import_users(export_users(options))

    assert error is None
    assert records == options["users"]


@pytest.mark.parametrize(
    "text",
    [
        "users:\n  - user_id: !env_var HAAC_TEST_SECRET\n    filter:\n      include_domains: [sensor]\n",
        "users:\n  - user_id: !include leaked.txt\n    filter:\n      include_domains: [sensor]\n",
    ],
)
async def test_import_never_resolves_home_assistant_tags(
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    text: str,
) -> None:
    anton = add_user("anton")
    monkeypatch.setenv("HAAC_TEST_SECRET", anton.id)
    (tmp_path / "leaked.txt").write_text(anton.id)
    monkeypatch.chdir(tmp_path)
    entry = await _add_entry(hass)

    result = await _menu(hass, entry, "import_yaml")
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"yaml": text})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_yaml"}
    assert entry.options == {}


async def test_a_user_deleted_while_the_form_is_open_is_not_added_back(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    entry = await _add_entry(hass)
    result = await _menu(hass, entry, "add_user")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": anton.id}
    )

    await hass.auth.async_remove_user(anton)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"include_domains": ["sensor"]}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "user_gone"
    assert entry.options.get("users", []) == []


async def test_changes_saved_meanwhile_are_kept(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    maria = add_user("maria")
    entry = await _add_entry(hass)
    first = await _menu(hass, entry, "add_user")
    first = await hass.config_entries.options.async_configure(
        first["flow_id"], {"user_id": anton.id}
    )

    second = await _menu(hass, entry, "add_user")
    second = await hass.config_entries.options.async_configure(
        second["flow_id"], {"user_id": maria.id}
    )
    await hass.config_entries.options.async_configure(
        second["flow_id"], {"include_domains": ["switch"]}
    )
    await hass.config_entries.options.async_configure(
        first["flow_id"], {"include_domains": ["sensor"]}
    )

    assert {record["user_id"] for record in entry.options["users"]} == {anton.id, maria.id}


async def test_names_form_shows_friendly_name_with_entity_id(
    hass: HomeAssistant, add_user: Callable[[str], User]
) -> None:
    anton = add_user("anton")
    entry = await _add_entry(hass)
    hass.states.async_set("sensor.humidity", "40", {"friendly_name": "Living room humidity"})

    result = await _menu(hass, entry, "add_user")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"user_id": anton.id}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"include_entities": ["sensor.humidity"]}
    )
    assert result["step_id"] == "names"
    label = "Living room humidity"
    assert [str(key) for key in result["data_schema"].schema] == [label]
    assert "`sensor.humidity`" in result["description_placeholders"]["entities"]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {label: "Humidity"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["users"][0]["names"] == {"sensor.humidity": "Humidity"}

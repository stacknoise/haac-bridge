"""Config flow and options flow: set up HAAC Bridge and choose per user what the app may see (concept 10.2)."""

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.entityfilter import (
    CONF_EXCLUDE_DOMAINS,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXCLUDE_ENTITY_GLOBS,
    CONF_INCLUDE_DOMAINS,
    CONF_INCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITY_GLOBS,
)
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
import voluptuous as vol

from .config.ui_users import FILTER_KEYS, INCLUDE_KEYS, user_options, users_of
from .config.ui_yaml import export_users, import_users
from .const import CONF_NAMES, CONF_USER_ID, CONF_USERS, DOMAIN, SUPPORTED_DOMAINS
from .core.runtime import get_data

_DOMAIN_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=list(SUPPORTED_DOMAINS), multiple=True, mode=SelectSelectorMode.LIST
    )
)
_ENTITY_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=list(SUPPORTED_DOMAINS), multiple=True)
)
_GLOB_SELECTOR = TextSelector(TextSelectorConfig(multiple=True))

_SELECTORS = {
    CONF_INCLUDE_DOMAINS: _DOMAIN_SELECTOR,
    CONF_INCLUDE_ENTITIES: _ENTITY_SELECTOR,
    CONF_INCLUDE_ENTITY_GLOBS: _GLOB_SELECTOR,
    CONF_EXCLUDE_DOMAINS: _DOMAIN_SELECTOR,
    CONF_EXCLUDE_ENTITIES: _ENTITY_SELECTOR,
    CONF_EXCLUDE_ENTITY_GLOBS: _GLOB_SELECTOR,
}
"""One selector per filter rule, in the order of the form."""

_GLOB_KEYS = (CONF_INCLUDE_ENTITY_GLOBS, CONF_EXCLUDE_ENTITY_GLOBS)

MENU_ADD = "add_user"
MENU_EDIT = "edit_user"
MENU_REMOVE = "remove_user"
MENU_EXPORT = "export_yaml"
MENU_IMPORT = "import_yaml"
CONF_YAML = "yaml"


class HaacBridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Adds HAAC Bridge once; the users are chosen afterwards in the options."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for a confirmation, then create the entry without any user."""
        if user_input is None:
            return self.async_show_form(step_id="user")
        return self.async_create_entry(title="HAAC Bridge", data={})

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Create the entry for an installation that is configured in YAML only (concept 19.5).

        The schedule entities need a config entry, so the bridge adds one by itself.
        """
        return self.async_create_entry(title="HAAC Bridge", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow that edits the users of this entry."""
        return HaacBridgeOptionsFlow()


class HaacBridgeOptionsFlow(OptionsFlow):
    """Menu to add, change, remove, export and import the users the app may show entities to (concept 10.2)."""

    def __init__(self) -> None:
        """Start without a user selected."""
        self._user_id: str | None = None
        self._rules: dict[str, list[str]] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the menu; changing, removing and exporting need an already configured user."""
        options = [MENU_ADD] if await self._async_free_users() else []
        if users_of(self.config_entry.options):
            options += [MENU_EDIT, MENU_REMOVE, MENU_EXPORT]
        return self.async_show_menu(step_id="init", menu_options=[*options, MENU_IMPORT])

    async def async_step_export_yaml(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the UI users as YAML to copy; confirming returns to the menu without a change."""
        if user_input is not None:
            return await self.async_step_init()
        return self.async_show_form(
            step_id=MENU_EXPORT,
            data_schema=vol.Schema({}),
            description_placeholders={"yaml": export_users(self.config_entry.options)},
        )

    async def async_step_import_yaml(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Take over users from pasted YAML; a user in the YAML replaces that user's entry here."""
        errors: dict[str, str] = {}
        text = (user_input or {}).get(CONF_YAML, "")
        if user_input is not None:
            records, error = import_users(text)
            if error is None and not await self._async_all_exist(records):
                error = "unknown_user"
            if error is None:
                imported = {record[CONF_USER_ID]: record for record in records}
                others = [
                    r
                    for r in users_of(self.config_entry.options)
                    if r[CONF_USER_ID] not in imported
                ]
                return self.async_create_entry(data={CONF_USERS: [*others, *imported.values()]})
            errors["base"] = error
        schema = vol.Schema(
            {
                vol.Required(CONF_YAML, description={"suggested_value": text}): TextSelector(
                    TextSelectorConfig(multiline=True)
                )
            }
        )
        return self.async_show_form(step_id=MENU_IMPORT, data_schema=schema, errors=errors)

    async def _async_all_exist(self, records: list[dict[str, Any]]) -> bool:
        """Return True if every record names an existing Home Assistant user."""
        users = {user.id for user in await self.hass.auth.async_get_users()}
        return all(record[CONF_USER_ID] in users for record in records)

    async def async_step_add_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose a Home Assistant user that has no entry yet."""
        free = await self._async_free_users()
        if user_input is not None:
            self._user_id = user_input[CONF_USER_ID]
            self._rules = {}
            return await self.async_step_filter()
        return self.async_show_form(step_id="add_user", data_schema=_user_schema(free))

    async def async_step_edit_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose one of the configured users to change."""
        if user_input is not None:
            self._user_id = user_input[CONF_USER_ID]
            self._rules = dict(self._record(self._user_id).get("filter", {}))
            return await self.async_step_filter()
        return self.async_show_form(
            step_id="edit_user", data_schema=_user_schema(await self._async_configured_users())
        )

    async def async_step_remove_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove a configured user; the app then shows this user no entities.

        If the user has schedules, a confirmation says how many are deleted with the entry.
        """
        if user_input is not None:
            self._user_id = user_input[CONF_USER_ID]
            if self._schedule_count(self._user_id):
                return await self.async_step_confirm_remove()
            return self._remove(self._user_id)
        return self.async_show_form(
            step_id="remove_user", data_schema=_user_schema(await self._async_configured_users())
        )

    async def async_step_confirm_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a confirmation that names the number of schedules that will be deleted."""
        if self._user_id is None:
            return self.async_abort(reason="unknown")
        if user_input is not None:
            return self._remove(self._user_id)
        user = await self.hass.auth.async_get_user(self._user_id)
        return self.async_show_form(
            step_id="confirm_remove",
            data_schema=vol.Schema({}),
            description_placeholders={
                "user": (user.name if user else None) or self._user_id,
                "count": str(self._schedule_count(self._user_id)),
            },
        )

    def _schedule_count(self, user_id: str | None) -> int:
        """Return how many schedules the user has."""
        return len(get_data(self.hass).schedules.store.by_owner(user_id)) if user_id else 0

    def _remove(self, user_id: str) -> ConfigFlowResult:
        """Save the options without this user; their schedules are deleted when the options apply."""
        remaining = [
            record
            for record in users_of(self.config_entry.options)
            if record[CONF_USER_ID] != user_id
        ]
        return self.async_create_entry(data={CONF_USERS: remaining})

    async def async_step_filter(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose which entities the user may see: domains, entities and wildcards to include or exclude."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._rules = {key: list(user_input.get(key, [])) for key in FILTER_KEYS}
            if not any(self._rules[key] for key in INCLUDE_KEYS):
                errors["base"] = "no_include"
            elif not _globs_valid(self._rules):
                errors["base"] = "invalid_glob"
            else:
                return await self.async_step_names()
        schema = vol.Schema(
            {
                vol.Optional(key, description={"suggested_value": self._rules.get(key)}): selector
                for key, selector in _SELECTORS.items()
            }
        )
        return self.async_show_form(step_id="filter", data_schema=schema, errors=errors)

    async def async_step_names(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Give the explicitly included entities display names for the app; empty keeps the Home Assistant name."""
        entity_ids = sorted(self._rules.get(CONF_INCLUDE_ENTITIES, []))
        if user_input is None and entity_ids:
            known = self._record(self._user_id).get(CONF_NAMES, {})
            schema = vol.Schema(
                {
                    vol.Optional(
                        entity_id, description={"suggested_value": known.get(entity_id)}
                    ): str
                    for entity_id in entity_ids
                }
            )
            return self.async_show_form(step_id="names", data_schema=schema)
        names = {
            entity_id: name.strip()
            for entity_id, name in (user_input or {}).items()
            if entity_id in entity_ids and name and name.strip()
        }
        return self._save(names)

    def _save(self, names: dict[str, str]) -> ConfigFlowResult:
        """Store the selected user's rules and names, replacing an earlier entry of this user."""
        if self._user_id is None:
            return self.async_abort(reason="unknown")
        record = user_options(self._user_id, self._rules, names)
        others = [
            r for r in users_of(self.config_entry.options) if r[CONF_USER_ID] != self._user_id
        ]
        return self.async_create_entry(data={CONF_USERS: [*others, record]})

    def _record(self, user_id: str | None) -> dict[str, Any]:
        """Return the stored record of a user, or an empty one."""
        return next(
            (r for r in users_of(self.config_entry.options) if r[CONF_USER_ID] == user_id), {}
        )

    async def _async_users(self) -> list[SelectOptionDict]:
        """Return every active, non-system Home Assistant user as a select option."""
        users = await self.hass.auth.async_get_users()
        return [
            SelectOptionDict(value=user.id, label=user.name or user.id)
            for user in sorted(users, key=lambda u: (u.name or "").casefold())
            if user.is_active and not user.system_generated
        ]

    async def _async_configured_users(self) -> list[SelectOptionDict]:
        """Return the users that already have an entry."""
        configured = {record[CONF_USER_ID] for record in users_of(self.config_entry.options)}
        return [user for user in await self._async_users() if user["value"] in configured]

    async def _async_free_users(self) -> list[SelectOptionDict]:
        """Return the users that have no entry yet."""
        configured = {record[CONF_USER_ID] for record in users_of(self.config_entry.options)}
        return [user for user in await self._async_users() if user["value"] not in configured]


def _user_schema(users: list[SelectOptionDict]) -> vol.Schema:
    """Return the form with one required choice of a user."""
    return vol.Schema(
        {
            vol.Required(CONF_USER_ID): SelectSelector(
                SelectSelectorConfig(options=users, mode=SelectSelectorMode.DROPDOWN)
            )
        }
    )


def _globs_valid(rules: dict[str, list[str]]) -> bool:
    """Return True if every wildcard has the form `domain.pattern`."""
    return all("." in glob and glob.strip() for key in _GLOB_KEYS for glob in rules.get(key, []))

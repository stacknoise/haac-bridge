# Code index – HAAC Bridge

> GENERATED FILE – do not edit by hand. Regenerate with `python scripts/code_index.py` (concept 18.5).

Lists every module, class and function of the integration with signature, file and a one-line summary, grouped by topic. Read it before writing code to reuse existing functions instead of duplicating them.

## (root)

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.__init__` | `module` | `custom_components/haac_bridge/__init__.py` | HAAC Bridge: per-user entity exposure for the HA Android Client (concept 10). |
| `async_setup` | `async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool` | `custom_components/haac_bridge/__init__.py` | Create the factories and exposure, register the commands and the reload action. |
| `async_setup._async_reload` | `async def _async_reload(call: ServiceCall) -> None` | `custom_components/haac_bridge/__init__.py` | Handle the haac_bridge.reload action. |
| `_async_start_schedules` | `async def _async_start_schedules(hass: HomeAssistant, schedules: ScheduleManager) -> None` | `custom_components/haac_bridge/__init__.py` | Load the schedules, plan them once HA has started and cancel the timers when it stops. |
| `_async_start_schedules._start` | `async def _start(_hass: HomeAssistant) -> None` | `custom_components/haac_bridge/__init__.py` | Plan every schedule once Home Assistant is running. |
| `_async_start_schedules._stop` | `def _stop(_event: Event) -> None` | `custom_components/haac_bridge/__init__.py` | Cancel all schedule timers when Home Assistant stops. |
| `_async_follow_exposure_inputs` | `def _async_follow_exposure_inputs(hass: HomeAssistant) -> None` | `custom_components/haac_bridge/__init__.py` | Clear the caches of the exposure when users, the entity registry or the set of entities change. |
| `_async_follow_exposure_inputs._users_changed` | `def _users_changed(_event: Event) -> None` | `custom_components/haac_bridge/__init__.py` | A HA user was added, changed or removed. |
| `_async_follow_exposure_inputs._registry_changed` | `def _registry_changed(_event: Event) -> None` | `custom_components/haac_bridge/__init__.py` | An entity was created, removed or changed in the entity registry. |
| `_async_follow_exposure_inputs._added_or_removed` | `def _added_or_removed(event_data: EventStateChangedData) -> bool` | `custom_components/haac_bridge/__init__.py` | Return True for an entity of a v1 domain that appeared or disappeared. |
| `_async_follow_exposure_inputs._states_changed` | `def _states_changed(_event: Event[EventStateChangedData]) -> None` | `custom_components/haac_bridge/__init__.py` | An entity appeared in or left the state machine. |
| `_async_listen_to_user_events` | `def _async_listen_to_user_events(hass: HomeAssistant) -> None` | `custom_components/haac_bridge/__init__.py` | Follow the deletion and the change of HA users with their schedules (concept 19.6). |
| `_async_listen_to_user_events._removed` | `async def _removed(event: Event) -> None` | `custom_components/haac_bridge/__init__.py` | A HA user was deleted: delete their schedules and their UI entry. |
| `_async_listen_to_user_events._updated` | `async def _updated(event: Event) -> None` | `custom_components/haac_bridge/__init__.py` | A HA user changed: pause their schedules if they are inactive, resume them otherwise. |
| `_async_user_removed` | `async def _async_user_removed(hass: HomeAssistant, user_id: str) -> None` | `custom_components/haac_bridge/__init__.py` | Delete the schedules and the UI entry of a deleted HA user (concept 19.6.1). |
| `async_reload` | `async def async_reload(hass: HomeAssistant) -> None` | `custom_components/haac_bridge/__init__.py` | Re-read the YAML configuration and rebuild the exposure of all users. |
| `_async_apply` | `async def _async_apply(hass: HomeAssistant, *, sweep: bool=True) -> None` | `custom_components/haac_bridge/__init__.py` | Rebuild the exposure from the YAML and UI entries and tell connected apps. |
| `async_setup_entry` | `async def async_setup_entry(hass: HomeAssistant, entry: HaacBridgeConfigEntry) -> bool` | `custom_components/haac_bridge/__init__.py` | Take over the UI users, follow option changes and create the entities of the schedules. |
| `_async_options_updated` | `async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None` | `custom_components/haac_bridge/__init__.py` | Apply changed options of the entry without reloading the integration. |
| `async_unload_entry` | `async def async_unload_entry(hass: HomeAssistant, entry: HaacBridgeConfigEntry) -> bool` | `custom_components/haac_bridge/__init__.py` | Unload the schedule entities and drop the UI users; the YAML users stay. |
| `async_remove_entry` | `async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None` | `custom_components/haac_bridge/__init__.py` | Delete all schedules and their storage file when the entry is removed (concept 19.6). |
| `haac_bridge.config_flow` | `module` | `custom_components/haac_bridge/config_flow.py` | Config flow and options flow: set up HAAC Bridge and choose per user what the app may see (concept 10.2). |
| `HaacBridgeConfigFlow` | `class HaacBridgeConfigFlow(ConfigFlow)` | `custom_components/haac_bridge/config_flow.py` | Adds HAAC Bridge once; the users are chosen afterwards in the options. |
| `HaacBridgeConfigFlow.async_step_user` | `async def async_step_user(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Ask for a confirmation, then create the entry without any user. |
| `HaacBridgeConfigFlow.async_step_import` | `async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Create the entry for an installation that is configured in YAML only (concept 19.5). |
| `HaacBridgeConfigFlow.async_get_options_flow` | `def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow` | `custom_components/haac_bridge/config_flow.py` | Return the options flow that edits the users of this entry. |
| `HaacBridgeOptionsFlow` | `class HaacBridgeOptionsFlow(OptionsFlow)` | `custom_components/haac_bridge/config_flow.py` | Menu to add, change, remove, export and import the users the app may show entities to (concept 10.2). |
| `HaacBridgeOptionsFlow.__init__` | `def __init__(self) -> None` | `custom_components/haac_bridge/config_flow.py` | Start without a user selected. |
| `HaacBridgeOptionsFlow.async_step_init` | `async def async_step_init(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Show the menu; changing, removing and exporting need an already configured user. |
| `HaacBridgeOptionsFlow.async_step_export_yaml` | `async def async_step_export_yaml(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Show the UI users as YAML to copy; confirming returns to the menu without a change. |
| `HaacBridgeOptionsFlow.async_step_import_yaml` | `async def async_step_import_yaml(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Take over users from pasted YAML; a user in the YAML replaces that user's entry here. |
| `HaacBridgeOptionsFlow._async_all_exist` | `async def _async_all_exist(self, records: list[dict[str, Any]]) -> bool` | `custom_components/haac_bridge/config_flow.py` | Return True if every record names an existing Home Assistant user. |
| `HaacBridgeOptionsFlow.async_step_add_user` | `async def async_step_add_user(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Choose a Home Assistant user that has no entry yet. |
| `HaacBridgeOptionsFlow.async_step_edit_user` | `async def async_step_edit_user(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Choose one of the configured users to change. |
| `HaacBridgeOptionsFlow.async_step_remove_user` | `async def async_step_remove_user(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Remove a configured user; the app then shows this user no entities. |
| `HaacBridgeOptionsFlow.async_step_confirm_remove` | `async def async_step_confirm_remove(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Ask for a confirmation that names the number of schedules that will be deleted. |
| `HaacBridgeOptionsFlow._schedule_count` | `def _schedule_count(self, user_id: str \| None) -> int` | `custom_components/haac_bridge/config_flow.py` | Return how many schedules the user has. |
| `HaacBridgeOptionsFlow._remove` | `def _remove(self, user_id: str) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Save the options without this user; their schedules are deleted when the options apply. |
| `HaacBridgeOptionsFlow.async_step_filter` | `async def async_step_filter(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Choose which entities the user may see: domains, entities and wildcards to include or exclude. |
| `HaacBridgeOptionsFlow.async_step_names` | `async def async_step_names(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Give the explicitly included entities display names for the app; empty keeps the Home Assistant name. |
| `HaacBridgeOptionsFlow._async_save` | `async def _async_save(self, names: dict[str, str]) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Store the selected user's rules and names, replacing an earlier entry of this user. |
| `HaacBridgeOptionsFlow._record` | `def _record(self, user_id: str \| None) -> dict[str, Any]` | `custom_components/haac_bridge/config_flow.py` | Return the stored record of a user, or an empty one. |
| `HaacBridgeOptionsFlow._async_users` | `async def _async_users(self) -> list[SelectOptionDict]` | `custom_components/haac_bridge/config_flow.py` | Return every active, non-system Home Assistant user as a select option. |
| `HaacBridgeOptionsFlow._async_configured_users` | `async def _async_configured_users(self) -> list[SelectOptionDict]` | `custom_components/haac_bridge/config_flow.py` | Return the users that already have an entry. |
| `HaacBridgeOptionsFlow._async_free_users` | `async def _async_free_users(self) -> list[SelectOptionDict]` | `custom_components/haac_bridge/config_flow.py` | Return the users that have no entry yet. |
| `_user_schema` | `def _user_schema(users: list[SelectOptionDict]) -> vol.Schema` | `custom_components/haac_bridge/config_flow.py` | Return the form with one required choice of a user. |
| `_globs_valid` | `def _globs_valid(rules: dict[str, list[str]]) -> bool` | `custom_components/haac_bridge/config_flow.py` | Return True if every wildcard has the form `domain.pattern`, with the YAML schema's check. |
| `haac_bridge.const` | `module` | `custom_components/haac_bridge/const.py` | Constants shared by all topics of HAAC Bridge. |
| `haac_bridge.sensor` | `module` | `custom_components/haac_bridge/sensor.py` | Sensor platform: the `next run` sensor of every schedule (concept 19.5). |
| `async_setup_entry` | `async def async_setup_entry(hass: HomeAssistant, entry: HaacBridgeConfigEntry, async_add_entities: AddEntitiesCallback) -> None` | `custom_components/haac_bridge/sensor.py` | Create the sensors of the existing schedules and of those added later. |
| `haac_bridge.switch` | `module` | `custom_components/haac_bridge/switch.py` | Switch platform: the `enabled` switch of every schedule (concept 19.5). |
| `async_setup_entry` | `async def async_setup_entry(hass: HomeAssistant, entry: HaacBridgeConfigEntry, async_add_entities: AddEntitiesCallback) -> None` | `custom_components/haac_bridge/switch.py` | Create the switches of the existing schedules and of those added later. |

## core

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.core.__init__` | `module` | `custom_components/haac_bridge/core/__init__.py` | Shared building blocks: errors, factories for errors and replies, command wrapper, runtime data. |
| `haac_bridge.core.caller` | `module` | `custom_components/haac_bridge/core/caller.py` | Resolves the calling HA user of a WebSocket request (concept 10.3). |
| `require_user` | `def require_user(connection: ActiveConnection) -> User` | `custom_components/haac_bridge/core/caller.py` | Return the HA user bound to the connection's access token, never a user named by the client. |
| `haac_bridge.core.command` | `module` | `custom_components/haac_bridge/core/command.py` | Command wrapper: every haac_bridge/* command runs through it (concept 18.3). |
| `SubscriptionStarted` | `class SubscriptionStarted` | `custom_components/haac_bridge/core/command.py` | Returned by a subscription handler: reply with an empty result, then send `initial` as first event (if any). |
| `BridgeCommand` | `class BridgeCommand` | `custom_components/haac_bridge/core/command.py` | A haac_bridge/* command: its type, request fields and handler. |
| `bridge_command` | `def bridge_command(command_type: str, fields: dict[Any, Any] \| None=None) -> Callable[[CommandHandler], BridgeCommand]` | `custom_components/haac_bridge/core/command.py` | Declare a handler as haac_bridge/* command with optional request fields. |
| `bridge_command.decorator` | `def decorator(handler: CommandHandler) -> BridgeCommand` | `custom_components/haac_bridge/core/command.py` | Wrap the handler into a BridgeCommand. |
| `async_register_commands` | `def async_register_commands(hass: HomeAssistant, commands: Iterable[BridgeCommand]) -> None` | `custom_components/haac_bridge/core/command.py` | Register all commands with HA's WebSocket API, each inside the wrapper. |
| `_wrap` | `def _wrap(command: BridgeCommand) -> websocket_api.WebSocketCommandHandler` | `custom_components/haac_bridge/core/command.py` | Build the HA handler that validates, runs and answers one command. |
| `_wrap._handle` | `async def _handle(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None` | `custom_components/haac_bridge/core/command.py` | Run the command and send exactly one reply (plus the first event of a subscription). |
| `_log_error` | `def _log_error(command_type: str, connection: ActiveConnection, code: ErrorCode, err: Exception) -> None` | `custom_components/haac_bridge/core/command.py` | Log a failed command once with its HAB code; tracebacks only for unexpected errors. |
| `haac_bridge.core.error_factory` | `module` | `custom_components/haac_bridge/core/error_factory.py` | ErrorFactory: turns any caught exception into a HaacBridgeError (concept 18.2, 18.3). |
| `ErrorFactory` | `class ErrorFactory` | `custom_components/haac_bridge/core/error_factory.py` | Maps exceptions to HaacBridgeError; the only place that decides an error's code. |
| `ErrorFactory.from_exception` | `def from_exception(self, err: Exception) -> HaacBridgeError` | `custom_components/haac_bridge/core/error_factory.py` | Return a HaacBridgeError for `err`; unknown exceptions become HAB-INT-000. |
| `haac_bridge.core.errors` | `module` | `custom_components/haac_bridge/core/errors.py` | All HAB error codes and the exception hierarchy of HAAC Bridge (concept 18.3). |
| `ErrorCode` | `class ErrorCode(StrEnum)` | `custom_components/haac_bridge/core/errors.py` | HAB error code; the value is the code, the lowercase name is the translation key. |
| `ErrorCode.translation_key` | `def translation_key(self) -> str` | `custom_components/haac_bridge/core/errors.py` | Return the key of the user text in translations/en.json. |
| `ErrorCode.area` | `def area(self) -> str` | `custom_components/haac_bridge/core/errors.py` | Return the area part of the code, e.g. `SVC` for `HAB-SVC-001`. |
| `HaacBridgeError` | `class HaacBridgeError(HomeAssistantError)` | `custom_components/haac_bridge/core/errors.py` | Base of every exception raised by HAAC Bridge; carries an ErrorCode. |
| `HaacBridgeError.__init__` | `def __init__(self, code: ErrorCode \| None=None, placeholders: dict[str, str] \| None=None) -> None` | `custom_components/haac_bridge/core/errors.py` | Create the error with its code and optional translation placeholders. |
| `ConfigError` | `class ConfigError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | Error in the haac_bridge YAML configuration (area CFG). |
| `NotAllowedError` | `class NotAllowedError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | The caller could not be identified or is deactivated (area AUTH). |
| `InvalidServiceError` | `class InvalidServiceError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | A service call was rejected or failed (area SVC). |
| `EntityNotFoundError` | `class EntityNotFoundError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | A requested entity does not exist (area ENT). |
| `HistoryError` | `class HistoryError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | History or statistics could not be read (area HIST). |
| `ScheduleError` | `class ScheduleError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | A schedule is invalid, missing, in conflict or not allowed (area SCH). |
| `RequestError` | `class RequestError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | A WebSocket request has an invalid format (area WS). |
| `InternalError` | `class InternalError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | Unexpected error inside the bridge (area INT). |
| `haac_bridge.core.response_factory` | `module` | `custom_components/haac_bridge/core/response_factory.py` | ResponseFactory: builds every WebSocket reply of HAAC Bridge (concept 11, 18.2). |
| `ResponseFactory` | `class ResponseFactory` | `custom_components/haac_bridge/core/response_factory.py` | Creates result and error messages in HA's WebSocket reply format. |
| `ResponseFactory.result` | `def result(self, msg_id: int, payload: Any) -> dict[str, Any]` | `custom_components/haac_bridge/core/response_factory.py` | Return a success reply carrying `payload`. |
| `ResponseFactory.event` | `def event(self, msg_id: int, payload: Any) -> dict[str, Any]` | `custom_components/haac_bridge/core/response_factory.py` | Return an event message of the subscription `msg_id`. |
| `ResponseFactory.state_diff` | `def state_diff(self, msg_id: int, event: Event[EventStateChangedData]) -> bytes` | `custom_components/haac_bridge/core/response_factory.py` | Return a state change as HA's compressed diff event, serialized once for all subscribers. |
| `ResponseFactory.error` | `def error(self, msg_id: int, error: HaacBridgeError) -> dict[str, Any]` | `custom_components/haac_bridge/core/response_factory.py` | Return an error reply whose `code` is the HAB code of `error`. |
| `haac_bridge.core.runtime` | `module` | `custom_components/haac_bridge/core/runtime.py` | Runtime data of HAAC Bridge stored in hass.data (concept 18.2). |
| `HaacBridgeData` | `class HaacBridgeData` | `custom_components/haac_bridge/core/runtime.py` | Factories, current exposure and the user entries of YAML and UI; created in async_setup. |
| `get_data` | `def get_data(hass: HomeAssistant) -> HaacBridgeData` | `custom_components/haac_bridge/core/runtime.py` | Return the runtime data of HAAC Bridge. |
| `haac_bridge.core.subscriptions` | `module` | `custom_components/haac_bridge/core/subscriptions.py` | Keeps one subscription of each kind per WebSocket connection (review finding S7). |
| `async_end_subscriptions_of` | `def async_end_subscriptions_of(connection: ActiveConnection, owner_type: type) -> None` | `custom_components/haac_bridge/core/subscriptions.py` | End every subscription of the connection whose stop callback belongs to an `owner_type` object. |

## config

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.config.__init__` | `module` | `custom_components/haac_bridge/config/__init__.py` | YAML configuration: schema, matching entries to HA users, Repairs issues. |
| `haac_bridge.config.repairs` | `module` | `custom_components/haac_bridge/config/repairs.py` | Reports configuration errors (HAB-CFG-*) in the log and in HA Repairs (concept 18.4). |
| `async_report_invalid_config` | `def async_report_invalid_config(hass: HomeAssistant, issue_ids: set[str]) -> None` | `custom_components/haac_bridge/config/repairs.py` | Log HAB-CFG-001 and create its Repairs issue; the previous configuration stays active. |
| `async_check_users` | `async def async_check_users(hass: HomeAssistant, issue_ids: set[str], entries: list[UserEntry], yaml_entries: list[UserEntry]) -> None` | `custom_components/haac_bridge/config/repairs.py` | Report entries without a HA user (HAB-CFG-002), YAML duplicates (HAB-CFG-003); remove resolved issues. |
| `_async_report_duplicates` | `async def _async_report_duplicates(hass: HomeAssistant, yaml_entries: list[UserEntry]) -> set[str]` | `custom_components/haac_bridge/config/repairs.py` | Create a HAB-CFG-003 issue for every HA user with more than one YAML entry; return the issue ids. |
| `haac_bridge.config.schema` | `module` | `custom_components/haac_bridge/config/schema.py` | YAML schema of the haac_bridge section in configuration.yaml (concept 10.2). |
| `valid_glob` | `def valid_glob(value: str) -> bool` | `custom_components/haac_bridge/config/schema.py` | Return True if a wildcard has the form `domain.pattern`, e.g. `sensor.*_humidity`. |
| `_globs_checked` | `def _globs_checked(rules: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/config/schema.py` | Voluptuous validator: reject a filter whose include or exclude wildcards are not `domain.pattern`. |
| `_none_as_empty` | `def _none_as_empty(section: Any) -> Any` | `custom_components/haac_bridge/config/schema.py` | Return an empty section for a bare `haac_bridge:` line, which YAML reads as None. |
| `UserEntry` | `class UserEntry` | `custom_components/haac_bridge/config/schema.py` | One validated entry under `users`: who it applies to, its filter and its entity names. |
| `UserEntry.label` | `def label(self) -> str` | `custom_components/haac_bridge/config/schema.py` | Return the name used for this entry in logs and Repairs. |
| `parse_users` | `def parse_users(config: ConfigType) -> list[UserEntry]` | `custom_components/haac_bridge/config/schema.py` | Return the user entries of a validated configuration; empty if the section is missing. |
| `_names` | `def _names(entity_config: dict[str, dict[str, str]]) -> dict[str, str]` | `custom_components/haac_bridge/config/schema.py` | Return entity ID to configured name for the entities that have a name. |
| `haac_bridge.config.ui_users` | `module` | `custom_components/haac_bridge/config/ui_users.py` | Users configured in the Home Assistant UI, stored in the options of the config entry (concept 10.2). |
| `user_options` | `def user_options(user_id: str, rules: Mapping[str, Any], names: Mapping[str, str]) -> dict[str, Any]` | `custom_components/haac_bridge/config/ui_users.py` | Return the options record of one user: its ID, the non-empty filter rules and the display names. |
| `users_of` | `def users_of(options: Mapping[str, Any]) -> list[dict[str, Any]]` | `custom_components/haac_bridge/config/ui_users.py` | Return the user records of the entry options; empty if none were configured. |
| `parse_ui_users` | `def parse_ui_users(options: Mapping[str, Any]) -> list[UserEntry]` | `custom_components/haac_bridge/config/ui_users.py` | Return the user entries of the entry options, with all six filter rules present as HA's filter expects. |
| `haac_bridge.config.ui_yaml` | `module` | `custom_components/haac_bridge/config/ui_yaml.py` | Export and import of the users configured in the UI as YAML (concept 10.2). |
| `export_users` | `def export_users(options: Mapping[str, Any]) -> str` | `custom_components/haac_bridge/config/ui_yaml.py` | Return the UI users as the `haac_bridge:` section of a configuration.yaml. |
| `import_users` | `def import_users(text: str) -> tuple[list[dict[str, Any]], str \| None]` | `custom_components/haac_bridge/config/ui_yaml.py` | Return the options records of the users in YAML [text], or the key of the error that stops the import. |
| `_section_of` | `def _section_of(text: str) -> dict[str, Any] \| None` | `custom_components/haac_bridge/config/ui_yaml.py` | Return the `haac_bridge:` content of YAML [text] (or the text itself when it has no such key), or None. |
| `_problem` | `def _problem(entries: list[UserEntry]) -> str \| None` | `custom_components/haac_bridge/config/ui_yaml.py` | Return the key of the first reason the entries cannot become UI users, or None. |
| `haac_bridge.config.users` | `module` | `custom_components/haac_bridge/config/users.py` | Matches configured user entries to Home Assistant users (concept 10.2, 10.3). |
| `normalize_username` | `def normalize_username(username: str) -> str` | `custom_components/haac_bridge/config/users.py` | Return the username in the form HA's own auth provider compares it. |
| `usernames_of` | `def usernames_of(user: User) -> set[str]` | `custom_components/haac_bridge/config/users.py` | Return the normalized login names of a user from its HA auth provider credentials. |
| `entry_matches` | `def entry_matches(entry: UserEntry, user: User) -> bool` | `custom_components/haac_bridge/config/users.py` | Return True if the configuration entry refers to this HA user. |
| `async_find_unknown_entries` | `async def async_find_unknown_entries(hass: HomeAssistant, entries: list[UserEntry]) -> list[UserEntry]` | `custom_components/haac_bridge/config/users.py` | Return the entries that match no existing HA user. |

## exposure

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.exposure.__init__` | `module` | `custom_components/haac_bridge/exposure/__init__.py` | Per-user exposure: entity filters, exposed set and revision. |
| `haac_bridge.exposure.exposure` | `module` | `custom_components/haac_bridge/exposure/exposure.py` | Per-user set of exposed entities and its revision hash (concept 10.2, 10.3). |
| `ExposureSnapshot` | `class ExposureSnapshot` | `custom_components/haac_bridge/exposure/exposure.py` | The entities exposed to one user at one moment, their configured names and revision. |
| `_UserRule` | `class _UserRule` | `custom_components/haac_bridge/exposure/exposure.py` | A configured user entry together with its built filter. |
| `_nothing_excluded` | `def _nothing_excluded(entity_id: str) -> bool` | `custom_components/haac_bridge/exposure/exposure.py` | Exclude no entity; the default when the caller has no entities of its own to hide. |
| `Exposure` | `class Exposure` | `custom_components/haac_bridge/exposure/exposure.py` | Decides which entities a HA user sees; deny by default for users not configured. |
| `Exposure.__init__` | `def __init__(self, entries: list[UserEntry], filters: FilterFactory, is_own_entity: Callable[[str], bool]=_nothing_excluded) -> None` | `custom_components/haac_bridge/exposure/exposure.py` | Build one filter per configured user entry; `is_own_entity` marks entities never exposed. |
| `Exposure.async_invalidate_users` | `def async_invalidate_users(self) -> None` | `custom_components/haac_bridge/exposure/exposure.py` | Forget everything; a HA user was added, changed or removed (login names can change). |
| `Exposure.async_invalidate_registry` | `def async_invalidate_registry(self) -> None` | `custom_components/haac_bridge/exposure/exposure.py` | Forget decisions and sets; the entity registry changed (own entities, renamed IDs). |
| `Exposure.async_invalidate_states` | `def async_invalidate_states(self) -> None` | `custom_components/haac_bridge/exposure/exposure.py` | Forget the exposed sets; an entity appeared in or left the state machine. |
| `Exposure.is_configured` | `def is_configured(self, user: User) -> bool` | `custom_components/haac_bridge/exposure/exposure.py` | Return True if the user has an entry in the YAML or the UI configuration. |
| `Exposure.is_exposed` | `def is_exposed(self, user: User, entity_id: str) -> bool` | `custom_components/haac_bridge/exposure/exposure.py` | Return True if the entity is in a v1 domain, passes the user's filter and is not the bridge's own. |
| `Exposure.filter_exposed` | `def filter_exposed(self, user: User, entity_ids: list[str]) -> list[str]` | `custom_components/haac_bridge/exposure/exposure.py` | Return the requested IDs the user may see, sorted and without duplicates. |
| `Exposure.exposed_entity_ids` | `def exposed_entity_ids(self, hass: HomeAssistant, user: User) -> list[str]` | `custom_components/haac_bridge/exposure/exposure.py` | Return the sorted IDs of all current entities exposed to the user. |
| `Exposure.configured_names` | `def configured_names(self, user: User) -> dict[str, str]` | `custom_components/haac_bridge/exposure/exposure.py` | Return the names from `entity_config` that apply to the user (global, then own). |
| `Exposure.snapshot` | `def snapshot(self, hass: HomeAssistant, user: User) -> ExposureSnapshot` | `custom_components/haac_bridge/exposure/exposure.py` | Return the user's exposed entities with their configured names and revision. |
| `Exposure._rule_for` | `def _rule_for(self, user: User) -> _UserRule \| None` | `custom_components/haac_bridge/exposure/exposure.py` | Return the first rule whose entry refers to the user, looked up once per user. |
| `compute_revision` | `def compute_revision(entity_ids: list[str], names: Mapping[str, str] \| None=None) -> str` | `custom_components/haac_bridge/exposure/exposure.py` | Return a stable hash of an exposed set and its configured names. |
| `haac_bridge.exposure.filter_factory` | `module` | `custom_components/haac_bridge/exposure/filter_factory.py` | FilterFactory: builds the entity filter of each configured user (concept 10.2, 18.2). |
| `_deny_all` | `def _deny_all(entity_id: str) -> bool` | `custom_components/haac_bridge/exposure/filter_factory.py` | Expose no entity; used for entries without any include rule. |
| `FilterFactory` | `class FilterFactory` | `custom_components/haac_bridge/exposure/filter_factory.py` | Creates entity filters with HA's entityfilter helper, so rules match the HomeKit Bridge. |
| `FilterFactory.create` | `def create(self, entry: UserEntry) -> EntityPredicate` | `custom_components/haac_bridge/exposure/filter_factory.py` | Return the filter for one user entry; without an include rule it exposes nothing. |
| `haac_bridge.exposure.own_entities` | `module` | `custom_components/haac_bridge/exposure/own_entities.py` | Recognises the entities HAAC Bridge creates itself, which are never exposed (concept 10.2, 19.5). |
| `_DeletedOwnEntities` | `class _DeletedOwnEntities` | `custom_components/haac_bridge/exposure/own_entities.py` | Entity IDs of deleted entities of the platform `haac_bridge`, rebuilt after registry changes. |
| `_DeletedOwnEntities.__init__` | `def __init__(self, hass: HomeAssistant) -> None` | `custom_components/haac_bridge/exposure/own_entities.py` | Start empty and follow the entity registry; the set is built on first use. |
| `_DeletedOwnEntities._async_invalidate` | `def _async_invalidate(self, _event: Event[er.EventEntityRegistryUpdatedData]) -> None` | `custom_components/haac_bridge/exposure/own_entities.py` | Forget the set; an entity was created, removed or changed. |
| `_DeletedOwnEntities.contains` | `def contains(self, entity_id: str) -> bool` | `custom_components/haac_bridge/exposure/own_entities.py` | Return True if a deleted registry entry of the bridge's platform had this entity ID. |
| `own_entity_checker` | `def own_entity_checker(hass: HomeAssistant) -> Callable[[str], bool]` | `custom_components/haac_bridge/exposure/own_entities.py` | Return a function that tells whether an entity ID belongs to the platform `haac_bridge`. |
| `own_entity_checker._is_own` | `def _is_own(entity_id: str) -> bool` | `custom_components/haac_bridge/exposure/own_entities.py` | Return True if the registry lists the entity, now or deleted, under the bridge's platform. |

## entities

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.entities.__init__` | `module` | `custom_components/haac_bridge/entities/__init__.py` | Entity descriptors sent to the app. |
| `haac_bridge.entities.descriptor_factory` | `module` | `custom_components/haac_bridge/entities/descriptor_factory.py` | DescriptorFactory: builds the entity descriptors sent to the app (concept 11.3, 18.2). |
| `_no_fields` | `def _no_fields(state: State, entry: er.RegistryEntry \| None) -> dict[str, Any]` | `custom_components/haac_bridge/entities/descriptor_factory.py` | Return no domain-specific fields (switch, climate: everything is in attributes). |
| `_sensor_fields` | `def _sensor_fields(state: State, entry: er.RegistryEntry \| None) -> dict[str, Any]` | `custom_components/haac_bridge/entities/descriptor_factory.py` | Return unit, state class and display precision a sensor tile needs (8.3). |
| `DescriptorFactory` | `class DescriptorFactory` | `custom_components/haac_bridge/entities/descriptor_factory.py` | Creates one descriptor per entity; the only place with per-domain field selection. |
| `DescriptorFactory.__init__` | `def __init__(self, hass: HomeAssistant) -> None` | `custom_components/haac_bridge/entities/descriptor_factory.py` | Keep the registries needed to resolve names and areas. |
| `DescriptorFactory.create` | `def create(self, state: State, configured_name: str \| None=None) -> dict[str, Any]` | `custom_components/haac_bridge/entities/descriptor_factory.py` | Return the descriptor of an entity including its current state and all attributes. |
| `DescriptorFactory.create_many` | `def create_many(self, entity_ids: list[str], names: Mapping[str, str] \| None=None) -> list[dict[str, Any]]` | `custom_components/haac_bridge/entities/descriptor_factory.py` | Return descriptors with configured names, skipping entities without a state. |
| `DescriptorFactory._area_name` | `def _area_name(self, entry: er.RegistryEntry \| None) -> str \| None` | `custom_components/haac_bridge/entities/descriptor_factory.py` | Return the HA area of the entity, or of its device if the entity has none. |
| `haac_bridge.entities.subscription` | `module` | `custom_components/haac_bridge/entities/subscription.py` | Live state subscription of one app connection (concept 9.2, 11.2). |
| `EntitySubscription` | `class EntitySubscription` | `custom_components/haac_bridge/entities/subscription.py` | Sends state changes of the entities exposed to one user to one WebSocket subscription. |
| `EntitySubscription.__init__` | `def __init__(self, hass: HomeAssistant, connection: ActiveConnection, msg_id: int, user: User) -> None` | `custom_components/haac_bridge/entities/subscription.py` | Keep everything needed to filter and send events; nothing is subscribed yet. |
| `EntitySubscription.async_start` | `def async_start(self) -> dict[str, Any]` | `custom_components/haac_bridge/entities/subscription.py` | Start listening and return the initial event with the states of all exposed entities. |
| `EntitySubscription.async_stop` | `def async_stop(self) -> None` | `custom_components/haac_bridge/entities/subscription.py` | Stop listening; called by HA when the app unsubscribes or the connection closes. |
| `EntitySubscription._async_is_relevant` | `def _async_is_relevant(self, event_data: EventStateChangedData) -> bool` | `custom_components/haac_bridge/entities/subscription.py` | Return True for entities already sent to the app or exposed to its user. |
| `EntitySubscription._async_on_state_changed` | `def _async_on_state_changed(self, event: Event[EventStateChangedData]) -> None` | `custom_components/haac_bridge/entities/subscription.py` | Forward a change, or report an entity that appeared in or left the exposed set. |
| `EntitySubscription._async_on_exposure_changed` | `def _async_on_exposure_changed(self) -> None` | `custom_components/haac_bridge/entities/subscription.py` | After a reload: send entities added to or removed from the set, then the new revision. |
| `EntitySubscription._send_exposure_changed` | `def _send_exposure_changed(self) -> None` | `custom_components/haac_bridge/entities/subscription.py` | Tell the app to run its revision check (concept 9.2). |
| `EntitySubscription._send` | `def _send(self, payload: dict[str, Any]) -> None` | `custom_components/haac_bridge/entities/subscription.py` | Send one event of this subscription. |
| `EntitySubscription._compressed_states` | `def _compressed_states(self, entity_ids: set[str]) -> dict[str, Any]` | `custom_components/haac_bridge/entities/subscription.py` | Return HA's compressed state for each entity that still has a state. |

## services

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.services.__init__` | `module` | `custom_components/haac_bridge/services/__init__.py` | Service calls: validated against the caller's exposure and executed with the caller's context. |
| `haac_bridge.services.call_factory` | `module` | `custom_components/haac_bridge/services/call_factory.py` | ServiceCallFactory: validated service calls for haac_bridge/call_service (concept 10.3, 11.4, 18.2). |
| `ValidatedServiceCall` | `class ValidatedServiceCall` | `custom_components/haac_bridge/services/call_factory.py` | A service call that passed all checks; the target is always exactly one entity. |
| `ServiceCallFactory` | `class ServiceCallFactory` | `custom_components/haac_bridge/services/call_factory.py` | Creates service calls only for exposed entities and services of the entity's own domain. |
| `ServiceCallFactory.__init__` | `def __init__(self, hass: HomeAssistant) -> None` | `custom_components/haac_bridge/services/call_factory.py` | Keep hass for state and service lookups. |
| `ServiceCallFactory.create` | `def create(self, exposure: Exposure, user: User, entity_id: str, service: str, data: dict[str, Any]) -> ValidatedServiceCall` | `custom_components/haac_bridge/services/call_factory.py` | Return the validated call or raise the matching HAB error (SVC-001, ENT-001, SVC-002, WS-001). |
| `async_execute` | `async def async_execute(hass: HomeAssistant, call: ValidatedServiceCall, *, context_user_id: str \| None=None) -> None` | `custom_components/haac_bridge/services/call_factory.py` | Run the call as the calling user, targeting only its entity; map HA errors to HAB codes. |

## history

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.history.__init__` | `module` | `custom_components/haac_bridge/history/__init__.py` | History and long-term statistics, read from the recorder for exposed entities only. |
| `haac_bridge.history.queries` | `module` | `custom_components/haac_bridge/history/queries.py` | Recorder queries for haac_bridge/history and haac_bridge/statistics (concept 8.1, 8.3, 10.3). |
| `utc_datetime` | `def utc_datetime(value: Any) -> datetime` | `custom_components/haac_bridge/history/queries.py` | Voluptuous validator: parse an ISO 8601 string into an aware UTC datetime. |
| `TimeRange` | `class TimeRange` | `custom_components/haac_bridge/history/queries.py` | Requested period in UTC; `end` None means up to now. |
| `TimeRange.__post_init__` | `def __post_init__(self) -> None` | `custom_components/haac_bridge/history/queries.py` | Reject a period that ends before it starts (HAB-WS-001). |
| `TimeRange.length` | `def length(self) -> timedelta` | `custom_components/haac_bridge/history/queries.py` | Return the length of the period; an open end counts up to now. |
| `TimeRange.check_length` | `def check_length(self, maximum: timedelta) -> None` | `custom_components/haac_bridge/history/queries.py` | Raise HAB-HIST-002 if the period is longer than `maximum`. |
| `TimeRange.in_future` | `def in_future(self) -> bool` | `custom_components/haac_bridge/history/queries.py` | Return True if the period starts after now, so there is nothing recorded. |
| `async_history` | `async def async_history(hass: HomeAssistant, entity_ids: list[str], period: TimeRange, minimal_response: bool) -> dict[str, list[dict[str, Any]]]` | `custom_components/haac_bridge/history/queries.py` | Return significant state changes per entity in HA's compressed state format. |
| `async_statistics` | `async def async_statistics(hass: HomeAssistant, entity_ids: list[str], period: TimeRange, resolution: str, types: list[str]) -> dict[str, list[dict[str, Any]]]` | `custom_components/haac_bridge/history/queries.py` | Return long-term statistics per entity; `start` and `end` of each row in milliseconds. |
| `_statistics_in_ms` | `def _statistics_in_ms(hass: HomeAssistant, statistic_ids: set[str], period: TimeRange, resolution: Any, types: Any) -> dict[str, list[dict[str, Any]]]` | `custom_components/haac_bridge/history/queries.py` | Query statistics in the executor and convert row timestamps to ms, as HA's own API does. |
| `_async_run` | `async def _async_run(hass: HomeAssistant, query: Callable[[], Any]) -> Any` | `custom_components/haac_bridge/history/queries.py` | Run a recorder query in its executor; database or recorder errors become HAB-HIST-001. |

## api

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.api.__init__` | `module` | `custom_components/haac_bridge/api/__init__.py` | The haac_bridge/* WebSocket commands, one module per command group (concept 11.2). |
| `haac_bridge.api.areas` | `module` | `custom_components/haac_bridge/api/areas.py` | Command haac_bridge/areas (concept 6.3, 11.2). |
| `ws_areas` | `async def ws_areas(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/areas.py` | Return the HA floors and areas that hold entities exposed to the caller. |
| `haac_bridge.api.entities` | `module` | `custom_components/haac_bridge/api/entities.py` | Commands haac_bridge/entities/list and haac_bridge/subscribe_entities (concept 11.2, 11.3). |
| `ws_entities_list` | `async def ws_entities_list(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/entities.py` | Return the revision and the descriptors of all entities exposed to the caller. |
| `ws_subscribe_entities` | `async def ws_subscribe_entities(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> SubscriptionStarted` | `custom_components/haac_bridge/api/entities.py` | Subscribe to the live states of the caller's exposed entities. |
| `haac_bridge.api.exposure` | `module` | `custom_components/haac_bridge/api/exposure.py` | Command haac_bridge/exposure/revision (concept 11.2). |
| `ws_exposure_revision` | `async def ws_exposure_revision(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/exposure.py` | Return the revision hash and entity count of the caller's exposed set. |
| `haac_bridge.api.history` | `module` | `custom_components/haac_bridge/api/history.py` | Commands haac_bridge/history and haac_bridge/statistics (concept 10.3, 11.2). |
| `_exposed_request` | `def _exposed_request(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> tuple[list[str], TimeRange]` | `custom_components/haac_bridge/api/history.py` | Return the requested entities the caller may see (none for a future period) and the period. |
| `ws_history` | `async def ws_history(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/history.py` | Return the state history of the requested entities that are exposed to the caller. |
| `ws_statistics` | `async def ws_statistics(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/history.py` | Return long-term statistics of the requested entities that are exposed to the caller. |
| `haac_bridge.api.info` | `module` | `custom_components/haac_bridge/api/info.py` | Command haac_bridge/info (concept 11.2, 11.4). |
| `ws_info` | `async def ws_info(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/info.py` | Return bridge, API and HA version, supported domains, instance ID and addresses. |
| `haac_bridge.api.schedules` | `module` | `custom_components/haac_bridge/api/schedules.py` | Commands haac_bridge/schedules/* and haac_bridge/subscribe_schedules (concept 11.2, 19.4). |
| `_fields` | `def _fields(msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/schedules.py` | Return the schedule fields of a request without the transport keys. |
| `ws_schedules_revision` | `async def ws_schedules_revision(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/schedules.py` | Return the revision and scope of the schedules the caller can see. |
| `ws_schedules_list` | `async def ws_schedules_list(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/schedules.py` | Return the schedules the caller can see, with the next run of each. |
| `ws_schedules_create` | `async def ws_schedules_create(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/schedules.py` | Create a schedule owned by the caller and return it. |
| `ws_schedules_update` | `async def ws_schedules_update(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/api/schedules.py` | Change a schedule the caller may edit and return it; the version must be the edited one. |
| `ws_schedules_delete` | `async def ws_schedules_delete(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None` | `custom_components/haac_bridge/api/schedules.py` | Delete a schedule the caller may edit; an unknown id is not an error. |
| `ws_schedules_run_now` | `async def ws_schedules_run_now(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None` | `custom_components/haac_bridge/api/schedules.py` | Start one run of a schedule now without changing its plan; the result follows as an event. |
| `ws_subscribe_schedules` | `async def ws_subscribe_schedules(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> SubscriptionStarted` | `custom_components/haac_bridge/api/schedules.py` | Subscribe to `schedules_changed` events for the schedules the caller can see. |
| `haac_bridge.api.services` | `module` | `custom_components/haac_bridge/api/services.py` | Command haac_bridge/call_service (concept 10.3, 11.2, 11.4). |
| `ws_call_service` | `async def ws_call_service(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None` | `custom_components/haac_bridge/api/services.py` | Call a service of an exposed entity's domain on that entity only. |

## areas

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.areas.__init__` | `module` | `custom_components/haac_bridge/areas/__init__.py` | HA floors and areas of the exposed entities, for the app's import wizard. |
| `haac_bridge.areas.catalog` | `module` | `custom_components/haac_bridge/areas/catalog.py` | Floors and areas that contain exposed entities (concept 6.3, 11.2). |
| `_area_of` | `def _area_of(entity: er.RegistryEntry, devices: dr.DeviceRegistry) -> str \| None` | `custom_components/haac_bridge/areas/catalog.py` | Return the area of an entity: its own, else the area of its device. |
| `_entity_counts` | `def _entity_counts(hass: HomeAssistant, entity_ids: Iterable[str]) -> Counter[str]` | `custom_components/haac_bridge/areas/catalog.py` | Count the given entities per area ID; entities without an area are left out. |
| `area_catalog` | `def area_catalog(hass: HomeAssistant, entity_ids: Iterable[str]) -> dict[str, Any]` | `custom_components/haac_bridge/areas/catalog.py` | Return the areas that hold at least one of the entities, and the floors those areas are on. |

## instance

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.instance.__init__` | `module` | `custom_components/haac_bridge/instance/__init__.py` | Identity of the Home Assistant instance: instance ID and the addresses it is reachable at. |
| `haac_bridge.instance.addresses` | `module` | `custom_components/haac_bridge/instance/addresses.py` | Instance ID and configured addresses of this Home Assistant instance (concept 4.3, 11.2). |
| `async_instance_identity` | `async def async_instance_identity(hass: HomeAssistant) -> dict[str, Any]` | `custom_components/haac_bridge/instance/addresses.py` | Return the instance ID and the internal, external and cloud address (each `None` if unset). |
| `_url_or_none` | `def _url_or_none(resolve: Callable[[], str]) -> str \| None` | `custom_components/haac_bridge/instance/addresses.py` | Return the URL `resolve` finds, or `None` if Home Assistant has none of that kind. |

## schedules

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.schedules.__init__` | `module` | `custom_components/haac_bridge/schedules/__init__.py` | Schedules: store, trigger planning, runner, user lifecycle and HA entities (concept 19). |
| `haac_bridge.schedules.entities` | `module` | `custom_components/haac_bridge/schedules/entities.py` | The HA entities of a schedule: an `enabled` switch and a `next run` sensor (concept 19.5). |
| `unique_id` | `def unique_id(schedule_id: str, suffix: str) -> str` | `custom_components/haac_bridge/schedules/entities.py` | Return the unique id of a schedule entity, e.g. `haac_bridge_schedule_<id>_enabled`. |
| `schedule_id_of` | `def schedule_id_of(entity_unique_id: str) -> str \| None` | `custom_components/haac_bridge/schedules/entities.py` | Return the schedule id inside a unique id of this integration, or None if it has another form. |
| `ScheduleEntity` | `class ScheduleEntity(Entity)` | `custom_components/haac_bridge/schedules/entities.py` | Common part of the schedule entities: it follows the schedule in the store. |
| `ScheduleEntity.__init__` | `def __init__(self, manager: ScheduleManager, schedule_id: str, suffix: str) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Remember the schedule this entity shows and give it its unique id. |
| `ScheduleEntity.schedule` | `def schedule(self) -> Schedule \| None` | `custom_components/haac_bridge/schedules/entities.py` | Return the schedule as it is stored now, or None if it was removed. |
| `ScheduleEntity.available` | `def available(self) -> bool` | `custom_components/haac_bridge/schedules/entities.py` | Return True while the schedule exists. |
| `ScheduleEntity.async_added_to_hass` | `async def async_added_to_hass(self) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Refresh when this schedule changes, runs or is paused, and when its owner is renamed. |
| `ScheduleEntity.async_update` | `async def async_update(self) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Look up the owner's name, which can only be read asynchronously; runs when added and on renames. |
| `ScheduleEntity._is_owner_event` | `def _is_owner_event(self, event_data: Mapping[str, Any]) -> bool` | `custom_components/haac_bridge/schedules/entities.py` | Return True for a user event about this schedule's owner. |
| `ScheduleEntity._handle_owner_change` | `def _handle_owner_change(self, _event: Event) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Read the owner's name again after the owner changed. |
| `ScheduleEntity._label` | `def _label(self) -> str \| None` | `custom_components/haac_bridge/schedules/entities.py` | Return the schedule name followed by its owner in brackets, so equal names stay apart. |
| `ScheduleEntity._handle_change` | `def _handle_change(self) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Write the state after this schedule changed; a removed schedule's entity is being removed. |
| `ScheduleEnabledSwitch` | `class ScheduleEnabledSwitch(ScheduleEntity, SwitchEntity)` | `custom_components/haac_bridge/schedules/entities.py` | Shows and sets whether the schedule is enabled; a system pause does not change it. |
| `ScheduleEnabledSwitch.__init__` | `def __init__(self, manager: ScheduleManager, schedule_id: str) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Create the switch of one schedule. |
| `ScheduleEnabledSwitch.name` | `def name(self) -> str \| None` | `custom_components/haac_bridge/schedules/entities.py` | Return the schedule name with its owner, which follows renames. |
| `ScheduleEnabledSwitch.is_on` | `def is_on(self) -> bool \| None` | `custom_components/haac_bridge/schedules/entities.py` | Return whether the schedule is enabled. |
| `ScheduleEnabledSwitch.async_turn_on` | `async def async_turn_on(self, **kwargs: Any) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Enable the schedule. |
| `ScheduleEnabledSwitch.async_turn_off` | `async def async_turn_off(self, **kwargs: Any) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Disable the schedule. |
| `ScheduleNextRunSensor` | `class ScheduleNextRunSensor(ScheduleEntity, SensorEntity)` | `custom_components/haac_bridge/schedules/entities.py` | Shows when the schedule runs next; unknown while it is disabled or paused. |
| `ScheduleNextRunSensor.__init__` | `def __init__(self, manager: ScheduleManager, schedule_id: str) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Create the sensor of one schedule. |
| `ScheduleNextRunSensor.name` | `def name(self) -> str \| None` | `custom_components/haac_bridge/schedules/entities.py` | Return the schedule name with its owner, followed by `next run`. |
| `ScheduleNextRunSensor.native_value` | `def native_value(self) -> datetime \| None` | `custom_components/haac_bridge/schedules/entities.py` | Return the planned time of the next run. |
| `ScheduleNextRunSensor.extra_state_attributes` | `def extra_state_attributes(self) -> dict[str, Any] \| None` | `custom_components/haac_bridge/schedules/entities.py` | Return owner, pause reason and last run. |
| `ScheduleEntityManager` | `class ScheduleEntityManager` | `custom_components/haac_bridge/schedules/entities.py` | Keeps one switch and one sensor per schedule in step with the store (concept 19.5). |
| `ScheduleEntityManager.__init__` | `def __init__(self, hass: HomeAssistant, manager: ScheduleManager, entry: ConfigEntry) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Remember the manager and start following schedule changes until the entry unloads. |
| `ScheduleEntityManager.async_setup_platform` | `def async_setup_platform(self, platform: str, async_add_entities: AddEntitiesCallback) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Take over the add function of a platform and create the entities of all schedules. |
| `ScheduleEntityManager.async_sweep` | `def async_sweep(self) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Remove registry entries whose schedule no longer exists (also after a missed removal). |
| `ScheduleEntityManager._async_sync` | `def _async_sync(self) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Create the entities of new schedules and remove those of removed ones. |
| `ScheduleEntityManager._async_remove` | `def _async_remove(self, schedule_ids: set[str]) -> None` | `custom_components/haac_bridge/schedules/entities.py` | Remove the entities of removed schedules from the registry, which also removes their states. |
| `haac_bridge.schedules.manager` | `module` | `custom_components/haac_bridge/schedules/manager.py` | ScheduleManager: store, planner and runner together, and the operations of the commands (concept 19.4). |
| `ScheduleManager` | `class ScheduleManager` | `custom_components/haac_bridge/schedules/manager.py` | Creates, changes, deletes, lists and runs schedules for the commands, as a given user. |
| `ScheduleManager.__init__` | `def __init__(self, hass: HomeAssistant) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Wire the store, the planner and the runner; call `async_load` and `async_start` next. |
| `ScheduleManager.async_load` | `async def async_load(self) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Read the schedules from storage. |
| `ScheduleManager.async_start` | `async def async_start(self) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Start planning; call when Home Assistant has started. |
| `ScheduleManager.async_stop` | `def async_stop(self) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Cancel all timers and the runs still going on in the background. |
| `ScheduleManager.notify` | `def notify(self, *schedule_ids: str) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Tell subscribers that schedules changed, ran, were paused or were removed. |
| `ScheduleManager._async_run_due` | `async def _async_run_due(self, schedule_id: str) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Run a schedule whose time has come. |
| `ScheduleManager.scope_of` | `def scope_of(user: User) -> str` | `custom_components/haac_bridge/schedules/manager.py` | Return `all` for admins, who see every schedule, and `own` for everybody else. |
| `ScheduleManager.visible_to` | `def visible_to(self, user: User) -> list[Schedule]` | `custom_components/haac_bridge/schedules/manager.py` | Return the schedules the user may see: all for admins, their own for others. |
| `ScheduleManager.revision_for` | `def revision_for(self, user: User) -> str` | `custom_components/haac_bridge/schedules/manager.py` | Return a hash over the visible schedules (id, version, pause, last run) and the scope. |
| `ScheduleManager.async_describe` | `async def async_describe(self, schedule: Schedule, user: User) -> dict[str, Any]` | `custom_components/haac_bridge/schedules/manager.py` | Return the stored form plus the owner's name, the computed next run and whether `user` owns it. |
| `ScheduleManager.async_list` | `async def async_list(self, user: User) -> dict[str, Any]` | `custom_components/haac_bridge/schedules/manager.py` | Return the revision, the scope and the visible schedules. |
| `ScheduleManager.async_create` | `async def async_create(self, user: User, fields: dict[str, Any]) -> Schedule` | `custom_components/haac_bridge/schedules/manager.py` | Create a schedule owned by `user` after validating it and the exposure of its entities. |
| `ScheduleManager.async_update` | `async def async_update(self, user: User, schedule_id: str, updated_at: str, fields: dict[str, Any]) -> Schedule` | `custom_components/haac_bridge/schedules/manager.py` | Change a schedule the user may edit; `updated_at` must be that of the edited version. |
| `ScheduleManager.async_set_enabled` | `async def async_set_enabled(self, schedule_id: str, *, enabled: bool) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Enable or disable a schedule, as its `enabled` switch in HA does (concept 19.5). |
| `ScheduleManager.async_wipe` | `async def async_wipe(self) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Delete every schedule and the storage file; called when the config entry is removed. |
| `ScheduleManager.async_delete` | `async def async_delete(self, user: User, schedule_id: str) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Delete a schedule the user may edit; an unknown id is not an error. |
| `ScheduleManager.async_run_now` | `async def async_run_now(self, user: User, schedule_id: str) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Start one run of a schedule now, as its owner, without changing the plan. |
| `ScheduleManager.async_sweep` | `async def async_sweep(self, owner_id: str \| None=None) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Delete the schedules of users who are gone or not configured, pause those of inactive ones. |
| `ScheduleManager.async_remove_owner` | `async def async_remove_owner(self, owner_id: str) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Delete every schedule of a user, as when the HA user was deleted (concept 19.6.1). |
| `ScheduleManager.async_remove` | `async def async_remove(self, schedule_ids: list[str]) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Remove schedules, stop their timers and tell subscribers. |
| `ScheduleManager._require` | `def _require(self, schedule_id: str) -> Schedule` | `custom_components/haac_bridge/schedules/manager.py` | Return the schedule or raise HAB-SCH-003. |
| `ScheduleManager._require_access` | `def _require_access(user: User, schedule: Schedule) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Allow the owner and admins; anybody else gets HAB-SCH-006. |
| `ScheduleManager._check_exposed` | `def _check_exposed(self, user: User, entities: tuple[str, ...]) -> None` | `custom_components/haac_bridge/schedules/manager.py` | Require every entity to be exposed to the user; the bridge's own entities never are. |
| `ScheduleManager._parse_changes` | `def _parse_changes(self, user: User, schedule: Schedule, fields: dict[str, Any]) -> dict[str, Any]` | `custom_components/haac_bridge/schedules/manager.py` | Return the validated changes of an update; only the owner may change the entities. |
| `ScheduleManager._with_owner_state` | `def _with_owner_state(self, schedule: Schedule, owner: User) -> Schedule` | `custom_components/haac_bridge/schedules/manager.py` | Return the schedule paused if its owner is inactive, or resumed if its pause has ended. |
| `ScheduleManager._without_ended_pause` | `def _without_ended_pause(self, schedule: Schedule, owner: User \| None) -> Schedule` | `custom_components/haac_bridge/schedules/manager.py` | Return the schedule without a pause whose cause is gone (concept 19.5). |
| `haac_bridge.schedules.model` | `module` | `custom_components/haac_bridge/schedules/model.py` | Schedule data model, validation and (de)serialisation (concept 19.2). |
| `WhenType` | `class WhenType(StrEnum)` | `custom_components/haac_bridge/schedules/model.py` | What triggers a schedule. |
| `Action` | `class Action(StrEnum)` | `custom_components/haac_bridge/schedules/model.py` | What a schedule does with its entities. |
| `PauseReason` | `class PauseReason(StrEnum)` | `custom_components/haac_bridge/schedules/model.py` | Why the system paused a schedule (concept 19.6). |
| `RunResult` | `class RunResult(StrEnum)` | `custom_components/haac_bridge/schedules/model.py` | Outcome of the last run. |
| `When` | `class When` | `custom_components/haac_bridge/schedules/model.py` | When a schedule runs: a wall-clock time or a sun event, on some weekdays. |
| `When.to_dict` | `def to_dict(self) -> dict[str, Any]` | `custom_components/haac_bridge/schedules/model.py` | Return the stored form; `time` only for fixed times, `offset_min` only for sun events. |
| `Paused` | `class Paused` | `custom_components/haac_bridge/schedules/model.py` | A pause set by the system, with its reason and the time it started. |
| `LastRun` | `class LastRun` | `custom_components/haac_bridge/schedules/model.py` | The outcome of the last run: when, the result and the HAB code if it was not ok. |
| `Schedule` | `class Schedule` | `custom_components/haac_bridge/schedules/model.py` | One schedule as stored by the bridge. |
| `Schedule.active` | `def active(self) -> bool` | `custom_components/haac_bridge/schedules/model.py` | Return whether the schedule is planned: enabled and not paused by the system. |
| `Schedule.to_dict` | `def to_dict(self) -> dict[str, Any]` | `custom_components/haac_bridge/schedules/model.py` | Return the stored (JSON) form. |
| `Schedule.with_changes` | `def with_changes(self, **changes: Any) -> Schedule` | `custom_components/haac_bridge/schedules/model.py` | Return a copy with the given fields replaced. |
| `_invalid` | `def _invalid() -> ScheduleError` | `custom_components/haac_bridge/schedules/model.py` | Return the error for a schedule that failed validation (HAB-SCH-001). |
| `_enum` | `def _enum(cls: type[_E], raw: object) -> _E` | `custom_components/haac_bridge/schedules/model.py` | Return the member of `cls` for a raw value, or raise HAB-SCH-001. |
| `_number` | `def _number(raw: object, low: int, high: int) -> int` | `custom_components/haac_bridge/schedules/model.py` | Return a whole number within the range; a bool does not count. |
| `parse_time` | `def parse_time(raw: object) -> time` | `custom_components/haac_bridge/schedules/model.py` | Return the time of a `HH:MM` text (24 h, no seconds). |
| `parse_days` | `def parse_days(raw: object) -> frozenset[int]` | `custom_components/haac_bridge/schedules/model.py` | Return the non-empty set of weekdays (0 = Monday). |
| `parse_when` | `def parse_when(raw: object) -> When` | `custom_components/haac_bridge/schedules/model.py` | Return the validated trigger: a time with weekdays, or a sun event with an offset. |
| `parse_name` | `def parse_name(raw: object) -> str` | `custom_components/haac_bridge/schedules/model.py` | Return the trimmed name of 1 to 60 characters. |
| `parse_action` | `def parse_action(raw: object) -> Action` | `custom_components/haac_bridge/schedules/model.py` | Return the validated action. |
| `parse_entities` | `def parse_entities(raw: object) -> tuple[str, ...]` | `custom_components/haac_bridge/schedules/model.py` | Return 1 to 20 distinct switch entity ids in the given order. |
| `parse_enabled` | `def parse_enabled(raw: object) -> bool` | `custom_components/haac_bridge/schedules/model.py` | Return the `enabled` flag; it must be a real boolean. |
| `new_schedule` | `def new_schedule(owner: str, fields: Mapping[str, Any], now: datetime \| None=None) -> Schedule` | `custom_components/haac_bridge/schedules/model.py` | Return a new schedule with a fresh id after validating `name`, `when`, `action`, `entities`. |
| `_parse_moment` | `def _parse_moment(raw: object) -> datetime` | `custom_components/haac_bridge/schedules/model.py` | Return the datetime of a stored ISO text. |
| `_parse_paused` | `def _parse_paused(raw: object) -> Paused \| None` | `custom_components/haac_bridge/schedules/model.py` | Return the stored pause, or None. |
| `_parse_last_run` | `def _parse_last_run(raw: object) -> LastRun \| None` | `custom_components/haac_bridge/schedules/model.py` | Return the stored last run, or None. |
| `schedule_from_dict` | `def schedule_from_dict(raw: object) -> Schedule` | `custom_components/haac_bridge/schedules/model.py` | Return the schedule of a stored dict, or raise HAB-SCH-001 if it is damaged. |
| `haac_bridge.schedules.planner` | `module` | `custom_components/haac_bridge/schedules/planner.py` | Plans the next run of every schedule and calls the runner when one is due (concept 19.3). |
| `SchedulePlanner` | `class SchedulePlanner` | `custom_components/haac_bridge/schedules/planner.py` | Keeps one timer per active schedule and re-plans after every run and every time change. |
| `SchedulePlanner.__init__` | `def __init__(self, hass: HomeAssistant, store: ScheduleStore, triggers: TriggerFactory, on_due: Callable[[str], Awaitable[None]], on_changed: Callable[[str], None]) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Create the planner; `on_due` runs a schedule, `on_changed` reports a pause or resume. |
| `SchedulePlanner.async_start` | `async def async_start(self) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Plan every schedule, follow time zone and location changes and catch up missed runs. |
| `SchedulePlanner.async_stop` | `def async_stop(self) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Cancel every timer and stop following configuration changes. |
| `SchedulePlanner.async_plan_all` | `async def async_plan_all(self) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Plan every schedule anew. |
| `SchedulePlanner.async_plan` | `async def async_plan(self, schedule_id: str, after: datetime \| None=None) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Plan the next run of one schedule, or cancel its timer if it is not active. |
| `SchedulePlanner.planned_run` | `def planned_run(self, schedule_id: str) -> datetime \| None` | `custom_components/haac_bridge/schedules/planner.py` | Return when the schedule runs next, or None if it is not planned. |
| `SchedulePlanner._cancel` | `def _cancel(self, schedule_id: str) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Cancel the timer of one schedule. |
| `SchedulePlanner._plannable` | `def _plannable(schedule: Schedule) -> bool` | `custom_components/haac_bridge/schedules/planner.py` | Return whether a timer is needed: enabled, and not paused for a reason a timer cannot fix. |
| `SchedulePlanner._make_job` | `def _make_job(self, schedule_id: str) -> Callable[[datetime], Awaitable[None]]` | `custom_components/haac_bridge/schedules/planner.py` | Return the timer callback of one schedule. |
| `SchedulePlanner._make_job._fire` | `async def _fire(_now: datetime) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Plan the next run first, so a failing run never stops the schedule, then run. |
| `SchedulePlanner._async_set_sun_pause` | `async def _async_set_sun_pause(self, schedule: Schedule, *, paused: bool) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Pause a sun schedule that has no event, or resume one whose event is back. |
| `SchedulePlanner._missed` | `def _missed(self, schedule: Schedule, now: datetime) -> bool` | `custom_components/haac_bridge/schedules/planner.py` | Return whether a run was due shortly before `now` and has not happened (concept 19.3). |
| `SchedulePlanner._handle_config_update` | `def _handle_config_update(self, _event: Event) -> None` | `custom_components/haac_bridge/schedules/planner.py` | Re-plan everything after a change of the time zone or the location. |
| `haac_bridge.schedules.runner` | `module` | `custom_components/haac_bridge/schedules/runner.py` | Runs one schedule: re-checks owner and exposure, switches the entities as the owner (concept 19.3). |
| `RunHooks` | `class RunHooks` | `custom_components/haac_bridge/schedules/runner.py` | What the runner asks the manager to do: remove schedules, re-plan one, announce a change. |
| `ScheduleRunner` | `class ScheduleRunner` | `custom_components/haac_bridge/schedules/runner.py` | Executes schedules one at a time per schedule. |
| `ScheduleRunner.__init__` | `def __init__(self, hass: HomeAssistant, store: ScheduleStore, hooks: RunHooks) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Keep what a run needs. |
| `ScheduleRunner.async_run_in_background` | `def async_run_in_background(self, schedule_id: str, triggered_by: str \| None=None) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Start a run without waiting for it; the result arrives as a schedule change (concept 19.4). |
| `ScheduleRunner.is_running` | `def is_running(self, schedule_id: str) -> bool` | `custom_components/haac_bridge/schedules/runner.py` | Return True while a run of the schedule is going on (including its wait to retry). |
| `ScheduleRunner.async_run_deferred` | `def async_run_deferred(self) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Start the runs that came due while the users were not loaded (review finding U2). |
| `ScheduleRunner.async_cancel_all` | `def async_cancel_all(self) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Cancel the runs started in the background, e.g. one waiting to retry, when HA stops. |
| `ScheduleRunner.async_run` | `async def async_run(self, schedule_id: str, triggered_by: str \| None=None) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Run a schedule now; a run of the same schedule that is still going on finishes first. |
| `ScheduleRunner._async_run_locked` | `async def _async_run_locked(self, schedule_id: str, triggered_by: str \| None) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Validate the owner and the exposure, then switch and record the result. |
| `ScheduleRunner._async_switch_all` | `async def _async_switch_all(self, user: User, schedule: Schedule, targets: list[str], context_user_id: str) -> int` | `custom_components/haac_bridge/schedules/runner.py` | Switch the entities in parallel, the unavailable ones after a short wait; return how many worked. |
| `ScheduleRunner._async_switch_many` | `async def _async_switch_many(self, user: User, entity_ids: list[str], service: str, context_user_id: str) -> int` | `custom_components/haac_bridge/schedules/runner.py` | Switch the entities at the same time; return how many worked. |
| `ScheduleRunner._async_wait_before_retry` | `async def _async_wait_before_retry(self) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Wait before unavailable entities are tried once more. |
| `ScheduleRunner._async_switch_one` | `async def _async_switch_one(self, user: User, entity_id: str, service: str, context_user_id: str) -> int` | `custom_components/haac_bridge/schedules/runner.py` | Call the service for one entity, checked against the owner; return 1 if it worked, else 0. |
| `ScheduleRunner._is_unavailable` | `def _is_unavailable(self, entity_id: str) -> bool` | `custom_components/haac_bridge/schedules/runner.py` | Return True if the entity's state is `unavailable`. |
| `ScheduleRunner._async_record` | `async def _async_record(self, schedule_id: str, result: RunResult) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Store the outcome of a run on the schedule as it is now. |
| `ScheduleRunner._async_pause` | `async def _async_pause(self, schedule_id: str, reason: PauseReason, last_run: LastRun \| None=None) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Pause a schedule for a reason, optionally with a failed last run, and stop its timer. |
| `ScheduleRunner._async_update` | `async def _async_update(self, schedule_id: str, *, last_run: LastRun \| None=None, paused: Paused \| None=None) -> None` | `custom_components/haac_bridge/schedules/runner.py` | Set `last_run` and `paused` (those that are given) on the current version and announce it. |
| `_result` | `def _result(done: int, total: int) -> RunResult` | `custom_components/haac_bridge/schedules/runner.py` | Return `ok` if every entity worked, `partial` if some did and `failed` if none did. |
| `haac_bridge.schedules.runtime` | `module` | `custom_components/haac_bridge/schedules/runtime.py` | The typed config entry of HAAC Bridge: its runtime data is the schedule entity manager. |
| `haac_bridge.schedules.store` | `module` | `custom_components/haac_bridge/schedules/store.py` | Persistent storage of the schedules in `.storage/haac_bridge.schedules` (concept 19.2). |
| `ScheduleStore` | `class ScheduleStore` | `custom_components/haac_bridge/schedules/store.py` | Holds all schedules in memory and writes them to storage after every change. |
| `ScheduleStore.__init__` | `def __init__(self, hass: HomeAssistant) -> None` | `custom_components/haac_bridge/schedules/store.py` | Create an empty store; call `async_load` before use. |
| `ScheduleStore.async_load` | `async def async_load(self) -> None` | `custom_components/haac_bridge/schedules/store.py` | Read the schedules from storage; a damaged entry is skipped and logged once. |
| `ScheduleStore.schedules` | `def schedules(self) -> list[Schedule]` | `custom_components/haac_bridge/schedules/store.py` | Return all schedules, oldest first; sorted once per change, not on every access. |
| `ScheduleStore.get` | `def get(self, schedule_id: str) -> Schedule \| None` | `custom_components/haac_bridge/schedules/store.py` | Return the schedule with this id, or None. |
| `ScheduleStore.by_owner` | `def by_owner(self, owner: str) -> list[Schedule]` | `custom_components/haac_bridge/schedules/store.py` | Return the schedules of one HA user, oldest first. |
| `ScheduleStore.async_add` | `async def async_add(self, schedule: Schedule) -> None` | `custom_components/haac_bridge/schedules/store.py` | Add a new schedule and save. |
| `ScheduleStore.async_replace` | `async def async_replace(self, schedule: Schedule, *, delay: bool=False) -> None` | `custom_components/haac_bridge/schedules/store.py` | Replace an existing schedule as a whole and save; an unknown id raises HAB-SCH-003. |
| `ScheduleStore.async_remove` | `async def async_remove(self, schedule_ids: Iterable[str]) -> list[Schedule]` | `custom_components/haac_bridge/schedules/store.py` | Remove the schedules with these ids, save once and return what was removed. |
| `ScheduleStore.async_apply_changes` | `async def async_apply_changes(self, replace: Iterable[Schedule]=(), remove: Iterable[str]=()) -> list[Schedule]` | `custom_components/haac_bridge/schedules/store.py` | Replace and remove schedules together with one save; return the removed schedules. |
| `ScheduleStore._async_save` | `async def _async_save(self) -> None` | `custom_components/haac_bridge/schedules/store.py` | Forget the sorted list and write all schedules to storage now (replaces a delayed write). |
| `ScheduleStore._data_to_save` | `def _data_to_save(self) -> dict[str, Any]` | `custom_components/haac_bridge/schedules/store.py` | Return the stored form of all schedules. |
| `ScheduleStore.async_remove_file` | `async def async_remove_file(self) -> None` | `custom_components/haac_bridge/schedules/store.py` | Delete the storage file when the config entry of the bridge is removed. |
| `haac_bridge.schedules.subscription` | `module` | `custom_components/haac_bridge/schedules/subscription.py` | Live subscription of one app connection to schedule changes (concept 19.4). |
| `ScheduleSubscription` | `class ScheduleSubscription` | `custom_components/haac_bridge/schedules/subscription.py` | Sends `schedules_changed` with the new revision whenever the caller's schedules change. |
| `ScheduleSubscription.__init__` | `def __init__(self, hass: HomeAssistant, connection: ActiveConnection, msg_id: int, user: User) -> None` | `custom_components/haac_bridge/schedules/subscription.py` | Keep what is needed to compute the revision and send events; nothing is subscribed yet. |
| `ScheduleSubscription.async_start` | `def async_start(self) -> None` | `custom_components/haac_bridge/schedules/subscription.py` | Remember the current revision and start listening; a previous one of the connection ends. |
| `ScheduleSubscription.async_stop` | `def async_stop(self) -> None` | `custom_components/haac_bridge/schedules/subscription.py` | Stop listening; called by HA when the app unsubscribes or the connection closes. |
| `ScheduleSubscription._async_on_changed` | `def _async_on_changed(self) -> None` | `custom_components/haac_bridge/schedules/subscription.py` | Send an event if the caller's view of the schedules changed. |
| `haac_bridge.schedules.triggers` | `module` | `custom_components/haac_bridge/schedules/triggers.py` | Trigger planners: when a schedule runs next and last ran (concept 19.3, 18.2 TriggerFactory). |
| `Trigger` | `class Trigger(Protocol)` | `custom_components/haac_bridge/schedules/triggers.py` | Computes the runs of one schedule; None means no run can be computed. |
| `Trigger.next_run` | `def next_run(self, after: datetime) -> datetime \| None` | `custom_components/haac_bridge/schedules/triggers.py` | Return the first run strictly after `after` (UTC), or None. |
| `Trigger.previous_run` | `def previous_run(self, before: datetime) -> datetime \| None` | `custom_components/haac_bridge/schedules/triggers.py` | Return the last run at or before `before` (UTC), or None. |
| `TimeTrigger` | `class TimeTrigger` | `custom_components/haac_bridge/schedules/triggers.py` | A fixed wall-clock time on some weekdays. |
| `TimeTrigger.__init__` | `def __init__(self, when: When, tz: tzinfo) -> None` | `custom_components/haac_bridge/schedules/triggers.py` | Remember the time, the weekdays and the time zone of the planning. |
| `TimeTrigger.next_run` | `def next_run(self, after: datetime) -> datetime \| None` | `custom_components/haac_bridge/schedules/triggers.py` | Return the first run after `after`, DST-safe. |
| `TimeTrigger.previous_run` | `def previous_run(self, before: datetime) -> datetime \| None` | `custom_components/haac_bridge/schedules/triggers.py` | Return the last run at or before `before`, DST-safe. |
| `SunTrigger` | `class SunTrigger` | `custom_components/haac_bridge/schedules/triggers.py` | Sunrise or sunset plus an offset, on some weekdays of the local date of the result. |
| `SunTrigger.__init__` | `def __init__(self, hass: HomeAssistant, when: When, event: str, tz: tzinfo) -> None` | `custom_components/haac_bridge/schedules/triggers.py` | Remember the sun event, the offset, the weekdays and the time zone. |
| `SunTrigger._instant` | `def _instant(self, day_offset: int, today: datetime) -> datetime \| None` | `custom_components/haac_bridge/schedules/triggers.py` | Return the run on the sun event of `today` plus `day_offset` days, or None. |
| `SunTrigger.next_run` | `def next_run(self, after: datetime) -> datetime \| None` | `custom_components/haac_bridge/schedules/triggers.py` | Return the first run after `after`; None if the sun never gives one within a year. |
| `SunTrigger.previous_run` | `def previous_run(self, before: datetime) -> datetime \| None` | `custom_components/haac_bridge/schedules/triggers.py` | Return the last run at or before `before`; None if there is none within a year. |
| `TriggerFactory` | `class TriggerFactory` | `custom_components/haac_bridge/schedules/triggers.py` | Creates the trigger planner that belongs to a schedule's `when` (concept 18.2). |
| `TriggerFactory.__init__` | `def __init__(self, hass: HomeAssistant) -> None` | `custom_components/haac_bridge/schedules/triggers.py` | Remember hass for the sun calculations. |
| `TriggerFactory.create` | `def create(self, when: When) -> Trigger` | `custom_components/haac_bridge/schedules/triggers.py` | Return the planner for this trigger, bound to the current HA time zone. |
| `haac_bridge.schedules.wall_time` | `module` | `custom_components/haac_bridge/schedules/wall_time.py` | Next and previous run of a fixed wall-clock time with weekdays, DST-safe (concept 19.3 step 4). |
| `_exists` | `def _exists(local: datetime) -> bool` | `custom_components/haac_bridge/schedules/wall_time.py` | Return whether the wall time exists in its zone (clocks going forward skip some). |
| `wall_instant` | `def wall_instant(day: date, at: time, tz: tzinfo) -> datetime` | `custom_components/haac_bridge/schedules/wall_time.py` | Return the UTC instant at which the wall time `at` is reached on `day` in `tz`. |
| `next_wall_run` | `def next_wall_run(after: datetime, days: Collection[int], at: time, tz: tzinfo) -> datetime \| None` | `custom_components/haac_bridge/schedules/wall_time.py` | Return the first run strictly after `after` on one of `days` (0 = Monday), or None. |
| `previous_wall_run` | `def previous_wall_run(before: datetime, days: Collection[int], at: time, tz: tzinfo) -> datetime \| None` | `custom_components/haac_bridge/schedules/wall_time.py` | Return the last run at or before `before` on one of `days` (0 = Monday), or None. |

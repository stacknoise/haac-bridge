# Code index – HAAC Bridge

> GENERATED FILE – do not edit by hand. Regenerate with `python scripts/code_index.py` (concept 18.5).

Lists every module, class and function of the integration with signature, file and a one-line summary, grouped by topic. Read it before writing code to reuse existing functions instead of duplicating them.

## (root)

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.__init__` | `module` | `custom_components/haac_bridge/__init__.py` | HAAC Bridge: per-user entity exposure for the HA Android Client (concept 10). |
| `async_setup` | `async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool` | `custom_components/haac_bridge/__init__.py` | Create the factories and exposure, register the commands and the reload action. |
| `async_setup._async_reload` | `async def _async_reload(call: ServiceCall) -> None` | `custom_components/haac_bridge/__init__.py` | Handle the haac_bridge.reload action. |
| `async_reload` | `async def async_reload(hass: HomeAssistant) -> None` | `custom_components/haac_bridge/__init__.py` | Re-read the YAML configuration and rebuild the exposure of all users. |
| `_async_apply` | `async def _async_apply(hass: HomeAssistant) -> None` | `custom_components/haac_bridge/__init__.py` | Rebuild the exposure from the YAML and UI entries and tell connected apps. |
| `async_setup_entry` | `async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool` | `custom_components/haac_bridge/__init__.py` | Take over the users configured in the UI and follow later changes of the options. |
| `_async_options_updated` | `async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None` | `custom_components/haac_bridge/__init__.py` | Apply changed options of the entry without reloading the integration. |
| `async_unload_entry` | `async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool` | `custom_components/haac_bridge/__init__.py` | Drop the UI users; the YAML users stay. |
| `haac_bridge.config_flow` | `module` | `custom_components/haac_bridge/config_flow.py` | Config flow and options flow: set up HAAC Bridge and choose per user what the app may see (concept 10.2). |
| `HaacBridgeConfigFlow` | `class HaacBridgeConfigFlow(ConfigFlow)` | `custom_components/haac_bridge/config_flow.py` | Adds HAAC Bridge once; the users are chosen afterwards in the options. |
| `HaacBridgeConfigFlow.async_step_user` | `async def async_step_user(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Ask for a confirmation, then create the entry without any user. |
| `HaacBridgeConfigFlow.async_get_options_flow` | `def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow` | `custom_components/haac_bridge/config_flow.py` | Return the options flow that edits the users of this entry. |
| `HaacBridgeOptionsFlow` | `class HaacBridgeOptionsFlow(OptionsFlow)` | `custom_components/haac_bridge/config_flow.py` | Menu to add, change and remove the users the app may show entities to (concept 10.2). |
| `HaacBridgeOptionsFlow.__init__` | `def __init__(self) -> None` | `custom_components/haac_bridge/config_flow.py` | Start without a user selected. |
| `HaacBridgeOptionsFlow.async_step_init` | `async def async_step_init(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Show the menu; changing or removing needs an already configured user. |
| `HaacBridgeOptionsFlow.async_step_add_user` | `async def async_step_add_user(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Choose a Home Assistant user that has no entry yet. |
| `HaacBridgeOptionsFlow.async_step_edit_user` | `async def async_step_edit_user(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Choose one of the configured users to change. |
| `HaacBridgeOptionsFlow.async_step_remove_user` | `async def async_step_remove_user(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Remove a configured user; the app then shows this user no entities. |
| `HaacBridgeOptionsFlow.async_step_filter` | `async def async_step_filter(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Choose which entities the user may see: domains, entities and wildcards to include or exclude. |
| `HaacBridgeOptionsFlow.async_step_names` | `async def async_step_names(self, user_input: dict[str, Any] \| None=None) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Give the explicitly included entities display names for the app; empty keeps the Home Assistant name. |
| `HaacBridgeOptionsFlow._save` | `def _save(self, names: dict[str, str]) -> ConfigFlowResult` | `custom_components/haac_bridge/config_flow.py` | Store the selected user's rules and names, replacing an earlier entry of this user. |
| `HaacBridgeOptionsFlow._record` | `def _record(self, user_id: str \| None) -> dict[str, Any]` | `custom_components/haac_bridge/config_flow.py` | Return the stored record of a user, or an empty one. |
| `HaacBridgeOptionsFlow._async_users` | `async def _async_users(self) -> list[SelectOptionDict]` | `custom_components/haac_bridge/config_flow.py` | Return every active, non-system Home Assistant user as a select option. |
| `HaacBridgeOptionsFlow._async_configured_users` | `async def _async_configured_users(self) -> list[SelectOptionDict]` | `custom_components/haac_bridge/config_flow.py` | Return the users that already have an entry. |
| `HaacBridgeOptionsFlow._async_free_users` | `async def _async_free_users(self) -> list[SelectOptionDict]` | `custom_components/haac_bridge/config_flow.py` | Return the users that have no entry yet. |
| `_user_schema` | `def _user_schema(users: list[SelectOptionDict]) -> vol.Schema` | `custom_components/haac_bridge/config_flow.py` | Return the form with one required choice of a user. |
| `_globs_valid` | `def _globs_valid(rules: dict[str, list[str]]) -> bool` | `custom_components/haac_bridge/config_flow.py` | Return True if every wildcard has the form `domain.pattern`. |
| `haac_bridge.const` | `module` | `custom_components/haac_bridge/const.py` | Constants shared by all topics of HAAC Bridge. |

## core

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.core.__init__` | `module` | `custom_components/haac_bridge/core/__init__.py` | Shared building blocks: errors, factories for errors and replies, command wrapper, runtime data. |
| `haac_bridge.core.caller` | `module` | `custom_components/haac_bridge/core/caller.py` | Resolves the calling HA user of a WebSocket request (concept 10.3). |
| `require_user` | `def require_user(connection: ActiveConnection) -> User` | `custom_components/haac_bridge/core/caller.py` | Return the HA user bound to the connection's access token, never a user named by the client. |
| `haac_bridge.core.command` | `module` | `custom_components/haac_bridge/core/command.py` | Command wrapper: every haac_bridge/* command runs through it (concept 18.3). |
| `SubscriptionStarted` | `class SubscriptionStarted` | `custom_components/haac_bridge/core/command.py` | Returned by a subscription handler: reply with an empty result, then send `initial` as first event. |
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
| `NotAllowedError` | `class NotAllowedError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | The caller could not be identified (area AUTH). |
| `InvalidServiceError` | `class InvalidServiceError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | A service call was rejected or failed (area SVC). |
| `EntityNotFoundError` | `class EntityNotFoundError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | A requested entity does not exist (area ENT). |
| `HistoryError` | `class HistoryError(HaacBridgeError)` | `custom_components/haac_bridge/core/errors.py` | History or statistics could not be read (area HIST). |
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

## config

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.config.__init__` | `module` | `custom_components/haac_bridge/config/__init__.py` | YAML configuration: schema, matching entries to HA users, Repairs issues. |
| `haac_bridge.config.repairs` | `module` | `custom_components/haac_bridge/config/repairs.py` | Reports configuration errors (HAB-CFG-*) in the log and in HA Repairs (concept 18.4). |
| `async_report_invalid_config` | `def async_report_invalid_config(hass: HomeAssistant, issue_ids: set[str]) -> None` | `custom_components/haac_bridge/config/repairs.py` | Log HAB-CFG-001 and create its Repairs issue; the previous configuration stays active. |
| `async_check_users` | `async def async_check_users(hass: HomeAssistant, issue_ids: set[str], entries: list[UserEntry]) -> None` | `custom_components/haac_bridge/config/repairs.py` | Report entries without a matching HA user (HAB-CFG-002) and remove resolved issues. |
| `haac_bridge.config.schema` | `module` | `custom_components/haac_bridge/config/schema.py` | YAML schema of the haac_bridge section in configuration.yaml (concept 10.2). |
| `_none_as_empty` | `def _none_as_empty(section: Any) -> Any` | `custom_components/haac_bridge/config/schema.py` | Return an empty section for a bare `haac_bridge:` line, which YAML reads as None. |
| `UserEntry` | `class UserEntry` | `custom_components/haac_bridge/config/schema.py` | One validated entry under `users`: who it applies to, its filter and its entity names. |
| `UserEntry.label` | `def label(self) -> str` | `custom_components/haac_bridge/config/schema.py` | Return the name used for this entry in logs and Repairs. |
| `parse_users` | `def parse_users(config: ConfigType) -> list[UserEntry]` | `custom_components/haac_bridge/config/schema.py` | Return the user entries of a validated configuration; empty if the section is missing. |
| `_names` | `def _names(entity_config: dict[str, dict[str, str]]) -> dict[str, str]` | `custom_components/haac_bridge/config/schema.py` | Return entity ID to configured name for the entities that have a name. |
| `haac_bridge.config.ui_users` | `module` | `custom_components/haac_bridge/config/ui_users.py` | Users configured in the Home Assistant UI, stored in the options of the config entry (concept 10.2). |
| `user_options` | `def user_options(user_id: str, rules: Mapping[str, Any], names: Mapping[str, str]) -> dict[str, Any]` | `custom_components/haac_bridge/config/ui_users.py` | Return the options record of one user: its ID, the non-empty filter rules and the display names. |
| `users_of` | `def users_of(options: Mapping[str, Any]) -> list[dict[str, Any]]` | `custom_components/haac_bridge/config/ui_users.py` | Return the user records of the entry options; empty if none were configured. |
| `parse_ui_users` | `def parse_ui_users(options: Mapping[str, Any]) -> list[UserEntry]` | `custom_components/haac_bridge/config/ui_users.py` | Return the user entries of the entry options, with all six filter rules present as HA's filter expects. |
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
| `Exposure` | `class Exposure` | `custom_components/haac_bridge/exposure/exposure.py` | Decides which entities a HA user sees; deny by default for users not configured. |
| `Exposure.__init__` | `def __init__(self, entries: list[UserEntry], filters: FilterFactory) -> None` | `custom_components/haac_bridge/exposure/exposure.py` | Build one filter per configured user entry. |
| `Exposure.is_exposed` | `def is_exposed(self, user: User, entity_id: str) -> bool` | `custom_components/haac_bridge/exposure/exposure.py` | Return True if the entity is in a v1 domain and passes the user's filter. |
| `Exposure.filter_exposed` | `def filter_exposed(self, user: User, entity_ids: list[str]) -> list[str]` | `custom_components/haac_bridge/exposure/exposure.py` | Return the requested IDs the user may see, sorted and without duplicates. |
| `Exposure.exposed_entity_ids` | `def exposed_entity_ids(self, hass: HomeAssistant, user: User) -> list[str]` | `custom_components/haac_bridge/exposure/exposure.py` | Return the sorted IDs of all current entities exposed to the user. |
| `Exposure.configured_names` | `def configured_names(self, user: User) -> dict[str, str]` | `custom_components/haac_bridge/exposure/exposure.py` | Return the names from `entity_config` that apply to the user (global, then own). |
| `Exposure.snapshot` | `def snapshot(self, hass: HomeAssistant, user: User) -> ExposureSnapshot` | `custom_components/haac_bridge/exposure/exposure.py` | Return the user's exposed entities with their configured names and revision. |
| `Exposure._rule_for` | `def _rule_for(self, user: User) -> _UserRule \| None` | `custom_components/haac_bridge/exposure/exposure.py` | Return the first rule whose entry refers to the user. |
| `compute_revision` | `def compute_revision(entity_ids: list[str], names: Mapping[str, str] \| None=None) -> str` | `custom_components/haac_bridge/exposure/exposure.py` | Return a stable hash of an exposed set and its configured names. |
| `haac_bridge.exposure.filter_factory` | `module` | `custom_components/haac_bridge/exposure/filter_factory.py` | FilterFactory: builds the entity filter of each configured user (concept 10.2, 18.2). |
| `_deny_all` | `def _deny_all(entity_id: str) -> bool` | `custom_components/haac_bridge/exposure/filter_factory.py` | Expose no entity; used for entries without any include rule. |
| `FilterFactory` | `class FilterFactory` | `custom_components/haac_bridge/exposure/filter_factory.py` | Creates entity filters with HA's entityfilter helper, so rules match the HomeKit Bridge. |
| `FilterFactory.create` | `def create(self, entry: UserEntry) -> EntityPredicate` | `custom_components/haac_bridge/exposure/filter_factory.py` | Return the filter for one user entry; without an include rule it exposes nothing. |

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
| `async_execute` | `async def async_execute(hass: HomeAssistant, call: ValidatedServiceCall) -> None` | `custom_components/haac_bridge/services/call_factory.py` | Run the call as the calling user, targeting only its entity; map HA errors to HAB codes. |

## history

| Symbol | Signature | File | Description |
| --- | --- | --- | --- |
| `haac_bridge.history.__init__` | `module` | `custom_components/haac_bridge/history/__init__.py` | History and long-term statistics, read from the recorder for exposed entities only. |
| `haac_bridge.history.queries` | `module` | `custom_components/haac_bridge/history/queries.py` | Recorder queries for haac_bridge/history and haac_bridge/statistics (concept 8.1, 8.3, 10.3). |
| `utc_datetime` | `def utc_datetime(value: Any) -> datetime` | `custom_components/haac_bridge/history/queries.py` | Voluptuous validator: parse an ISO 8601 string into an aware UTC datetime. |
| `TimeRange` | `class TimeRange` | `custom_components/haac_bridge/history/queries.py` | Requested period in UTC; `end` None means up to now. |
| `TimeRange.__post_init__` | `def __post_init__(self) -> None` | `custom_components/haac_bridge/history/queries.py` | Reject a period that ends before it starts (HAB-WS-001). |
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

# HAAC Bridge

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://img.shields.io/badge/HACS-Add%20repository-41BDF5?logo=homeassistantcommunitystore&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stacknoise&repository=haac-bridge&category=integration)

Home Assistant custom integration that gives the **HA Android Client (HAAC)** a filtered, per-user view of your entities. Unlike the official Companion App, which shows a user everything they can reach, HAAC only ever sees the entities **you share with that user, one by one**.

> This project is not affiliated with or endorsed by Home Assistant, the Open Home Foundation or Nabu Casa.

- Requires Home Assistant **2026.9.0** or newer.
- Supported entity domains in v1: `switch`, `sensor`, `climate`.
- App: [stacknoise/haac-android](https://github.com/stacknoise/haac-android)

## Features

**Sharing entities per user**
- Choose, per Home Assistant user, which entities the app may show and control: whole domains, single entities and wildcards such as `sensor.*_humidity`, each to include or to exclude. An explicit exclusion always wins, as in the HomeKit Bridge (the filter is built with Home Assistant's own `entityfilter` helper).
- **Deny by default:** a user who is not configured, or has no include rule, sees nothing. Only `switch`, `sensor` and `climate` are ever shared, whatever the filter says.
- Configure it in the **Home Assistant UI** (config and options flow, changes apply at once) or in `configuration.yaml`, or both; YAML entries win for a user who is in both. Users are identified by login name or by the stable user ID.
- Optional display names per entity, global or per user; the app shows them until the user renames the entity locally. A name never shares an entity by itself.
- New entities that match a filter are shared automatically, and connected apps are told at once (`exposure_changed`), also after a configuration change.

**What the app can do through the bridge**
- Read the shared entities with their current state, and follow their live changes.
- Call services on shared entities only: the entity must be shared with the caller, the service must be on the bridge's short list for the entity's domain (the ones the app uses, see concept 11.4), and the bridge sets the target itself, so a client cannot add other targets. A call that takes longer than 15 seconds counts as failed.
- Read history and long-term statistics of shared entities only, filtered before the recorder is queried; at most 50 entities per request, up to 366 days of history, 32 days of hourly and 5 years of daily statistics.
- Read the Home Assistant floors and areas that hold shared entities, so the app can offer an import of levels and rooms (no entity IDs are sent).
- Report the Home Assistant version, the bridge and API version, the instance ID and the internal, external and cloud address, so the app can recognise the same Home Assistant under different addresses.

**Schedules (time-controlled actions)**
- Users create schedules in the app, for example "every weekday at 06:45 turn the light on". A schedule switches `switch` entities (turn on, turn off or toggle) at a fixed time on chosen weekdays, or at sunrise or sunset with an offset of up to 3 hours.
- Schedules are stored and run **by the bridge**, so they work with the app closed, the phone off or on another network. They run in the context of their owner, so the logbook shows who triggered them (a manual run in the context of the user who started it), and at every run the bridge checks again that the owner still exists and may see each entity.
- Each schedule appears in Home Assistant as an *enabled* switch and a *next run* timestamp sensor on the device **HAAC Schedules**, named after the schedule and its owner, for example *Wake up (Anton)*, so equal names of two users stay apart. Turning the switch off pauses the schedule. These entities are never shared with app users, whatever a filter says.
- Home Assistant administrators see and manage all schedules in the app; the entity list of a foreign schedule can only be changed by its owner.
- Schedules follow the users: they are deleted at once when their owner is removed from the bridge configuration or deleted in Home Assistant, and paused while the owner is deactivated. Removing the integration deletes all schedules; while it is disabled or reloading, schedules are kept and wait.
- Schedules need the integration to have a configuration entry. If you configure the bridge in `configuration.yaml` only, it adds the entry by itself. Schedules are saved in `.storage/haac_bridge.schedules`, which a full Home Assistant backup includes.
- Times are Home Assistant's local time. A time that does not exist on the day the clocks go forward runs at the first minute after the gap; a time that occurs twice runs once.

**Safety and operations**
- The caller is always the Home Assistant user behind the access token; the app cannot ask for another user's entities.
- Stable error codes (`HAB-…`) with plain-language messages, configuration problems and unknown users as *Repairs* issues, and the action `haac_bridge.reload` to re-read the YAML.
- Distributed through HACS; CI runs hassfest, HACS validation, ruff, bandit, CodeQL and the tests.

## Installation (HACS)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stacknoise&repository=haac-bridge&category=integration)

1. Click the button above to open the repository in HACS, or in HACS open *Custom repositories* and add `https://github.com/stacknoise/haac-bridge` with category **Integration**.
2. Install **HAAC Bridge** and restart Home Assistant.
3. Choose which users may see which entities, in the Home Assistant UI or in `configuration.yaml` (see *Configuration* below).

## Configuration

You can configure the users in the Home Assistant UI, in `configuration.yaml`, or both.

### In the UI

1. Open *Settings → Devices & services → Add integration* and add **HAAC Bridge** (once).
2. Open the integration and choose *Configure*. Add a Home Assistant user, then choose what that user may see: domains, single entities and wildcards to include, and the same to exclude (an exclusion always wins). Include at least one rule, otherwise the user sees nothing.
3. Optionally give the entities you included one by one a name for the app.

Changes take effect at once, no restart or reload needed. Advanced or shared setups can still use YAML. If a user is configured in both places, the YAML entry is used and the UI entry for that user is ignored. The UI identifies users by their stable user ID, so renaming a Home Assistant user does not break the entry.

*Export as YAML* in the same menu shows the users configured in the UI as a `haac_bridge:` section, ready to copy into `configuration.yaml` or to keep as a backup (the UI data lives in `.storage/core.config_entries`, which a backup of `configuration.yaml` alone does not contain). *Import from YAML* takes such a section, or just its content, and adds the users; a user who is already configured in the UI is replaced, the others stay. Imported users are named by `user_id`, need at least one `include_*` rule, and must exist in Home Assistant. A bare `haac_bridge:` line in `configuration.yaml` counts as no users, so you can use the UI alone.

### In `configuration.yaml`

```yaml
haac_bridge:
  entity_config:                     # optional names for all users
    sensor.outdoor_temperature:
      name: Outside
  users:
    - username: anton                # HA login name, or user_id: <uuid>
      filter:
        include_domains:
          - climate
        include_entities:
          - switch.garage_socket
          - sensor.living_room_temperature
        include_entity_globs:
          - sensor.*_humidity
        exclude_entities:
          - climate.server_room
    - username: guest
      filter:
        include_entities:
          - sensor.outdoor_temperature
      entity_config:                 # optional names for this user only
        sensor.outdoor_temperature:
          name: Temperature outside
```

| Key | Meaning |
| --- | --- |
| `users[].username` / `users[].user_id` | The Home Assistant user. `user_id` survives renames and is preferred for production. |
| `filter.include_domains` / `exclude_domains` | Whole domains |
| `filter.include_entities` / `exclude_entities` | Single entity IDs |
| `filter.include_entity_globs` / `exclude_entity_globs` | Wildcards such as `sensor.*_temperature` |
| `entity_config.<entity_id>.name` | Name the app shows for the entity instead of the Home Assistant name, until the user renames it in the app. Under `users[]` it overrides the global one for that user. It does not share the entity; the filter decides that. |

Rules:

- **Deny by default.** A user who is not configured (in the UI or in YAML) sees no entities. A listed user without any `include_*` rule also sees none.
- An explicit exclude beats an include, as in the HomeKit Bridge.
- Only `switch`, `sensor` and `climate` entities are ever shared, whatever the filter says.
- New entities that match a filter (for example via a glob) are shared automatically.
- After editing the configuration, run the action **`haac_bridge.reload`** (admin only) or restart Home Assistant. Configuration problems appear under *Settings → Repairs*.

## Security note

The exposure limits what the app shows and controls through the `haac_bridge/*` commands. It is **not** a Home Assistant permission: Home Assistant has no per-entity permissions, so anyone holding a user's access token can still use Home Assistant's standard API directly.

- Create a dedicated **non-admin** Home Assistant user for each app user and never sign in to the app with an admin account.
- Do not rely on the exposure to separate users who do not trust each other.
- Tokens can be revoked per device in the user profile in Home Assistant.

## WebSocket API

The app talks to the bridge over Home Assistant's WebSocket API with commands prefixed `haac_bridge/`. Errors carry a code `HAB-<AREA>-<NNN>`, listed in [docs/error-codes.md](docs/error-codes.md).

| Command | Request fields | Reply |
| --- | --- | --- |
| `haac_bridge/info` | – | Bridge version, API version, supported domains, HA version, `instance_id` (Home Assistant's unique ID, also announced via zeroconf as `uuid`) and `urls` with the `internal`, `external` and `cloud` (Home Assistant Cloud remote UI) address, each `null` if not configured |
| `haac_bridge/exposure/revision` | – | `revision`, `entity_count` |
| `haac_bridge/entities/list` | – | `revision`, entity descriptors incl. current state; `name` is the Home Assistant name, `configured_name` the name from `entity_config` or `null` |
| `haac_bridge/subscribe_entities` | – | Empty result, then events: `{"a": {…}}` initial and added states, `{"c": {…}}` changes, `{"r": […]}` removals (Home Assistant's compressed state format), and `{"exposure_changed": {"revision": …}}` whenever the exposed set changes or the configuration is reloaded |
| `haac_bridge/call_service` | `entity_id`, `service`, `service_data` | Empty result, or an error: `HAB-SVC-001` not exposed, `HAB-ENT-001` entity gone, `HAB-SVC-002` service not allowed for the entity's domain, `HAB-WS-001` target keys or other keys than the service accepts in `service_data`, `HAB-SVC-003` Home Assistant failed or took longer than 15 seconds |
| `haac_bridge/history` | `entity_ids`, `start`, `end`?, `minimal_response`? | Significant state changes per entity in Home Assistant's compressed state format; at most 50 entities and 366 days (`HAB-HIST-002`); `HAB-HIST-001` if the recorder fails |
| `haac_bridge/statistics` | `entity_ids`, `start`, `end`?, `period` (`hour`, `day`, `week`, `month`), `types` (`mean`, `min`, `max`, `sum`) | Long-term statistics rows per entity; `start`/`end` of each row in milliseconds; at most 50 entities, 32 days for `hour` and 5 years otherwise (`HAB-HIST-002`) |
| `haac_bridge/areas` | – | `floors` (`floor_id`, `name`, `level`) and `areas` (`area_id`, `name`, `floor_id`, `entity_count`) of the Home Assistant registries, limited to areas that hold at least one entity exposed to the caller and the floors of those areas; no entity IDs. For the import wizard of the app |

The schedule commands are `haac_bridge/schedules/revision`, `list`, `create`, `update`, `delete` and `run_now` and `haac_bridge/subscribe_schedules` (event `{"schedules_changed": {"revision": …}}`). `update`, `delete` and `run_now` name the schedule with `schedule_id`; `run_now` replies as soon as the run has started, its result follows as `last_run` with `schedules_changed`, and the same schedule can be run by hand again after 10 seconds (`HAB-SCH-007`); `update` also needs the `updated_at` of the version that was edited (`HAB-SCH-004` if it changed in the meantime). Every schedule in `list`, `create` and `update` replies carries `own`, which is true if the caller is the owner (the app uses it to tell its own schedules from foreign ones in the administrator scope). `haac_bridge/info` lists `features: ["schedules"]`. Regular users see only their own schedules, administrators all of them (`scope`). See concept chapter 19 and [docs/error-codes.md](docs/error-codes.md) for the `HAB-SCH-*` codes.

History and statistics only include requested entities that are exposed to the caller; others are left out silently. Times are ISO 8601; a period in the future returns an empty result.

The bridge sets the service target itself and runs the call in the context of the signed-in user.

The app uses `instance_id` to recognise the same Home Assistant under different addresses and switches between the internal and the external address automatically. Set the addresses under *Settings → System → Network* in Home Assistant.

## Development

Read the [developer guide](docs/development.md), [CLAUDE.md](CLAUDE.md) and [docs/concept.md](docs/concept.md) (chapters 10, 11, 13 and 18) first.

```bash
pip install -r requirements_test.txt -r requirements_lint.txt   # Python 3.14
pytest
ruff check . && ruff format --check .
bandit -c pyproject.toml -r custom_components scripts
python scripts/code_index.py          # regenerate docs/code-index.md and docs/error-codes.md
```

## License

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE).

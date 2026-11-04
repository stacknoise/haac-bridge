# Configuration

Back to the [README](../README.md). A short version is in the README; this page has every option.

You can configure the users in the Home Assistant UI, in `configuration.yaml`, or both.

## In the UI

1. Open *Settings → Devices & services → Add integration* and add **HAAC Bridge** (once).
2. Open the integration and choose *Configure*. Add a Home Assistant user, then choose what that user may see: domains, single entities and wildcards to include, and the same to exclude (an exclusion always wins). Include at least one rule, otherwise the user sees nothing.
3. Optionally give the entities you included one by one a name for the app.

Changes take effect at once, no restart or reload needed. Advanced or shared setups can still use YAML. If a user is configured in both places, the YAML entry is used and the UI entry for that user is ignored. The UI identifies users by their stable user ID, so renaming a Home Assistant user does not break the entry.

*Export as YAML* in the same menu shows the users configured in the UI as a `haac_bridge:` section, ready to copy into `configuration.yaml` or to keep as a backup (the UI data lives in `.storage/core.config_entries`, which a backup of `configuration.yaml` alone does not contain). *Import from YAML* takes such a section, or just its content, and adds the users; a user who is already configured in the UI is replaced, the others stay. Imported users are named by `user_id`, need at least one `include_*` rule, and must exist in Home Assistant. A bare `haac_bridge:` line in `configuration.yaml` counts as no users, so you can use the UI alone.

## Logging

Under *Configure → Logging* you choose the log level (`debug`, `info`, `warning`, `error`; default `warning`) and whether switching actions appear on the Activity page (default: yes). The same settings can be made in `configuration.yaml`, where they win over the UI:

```yaml
haac_bridge:
  logging:
    level: info        # debug | info | warning | error
    activity: true     # show switching actions on the Activity page
```

The level takes effect at once, without a restart. The action log needs `info`; at the default `warning` only problems are logged.

## In `configuration.yaml`

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
| `users[].username` / `users[].user_id` | The Home Assistant user. `user_id` survives renames and is preferred for production. A `username` entry follows the login name: if a user is deleted and created again under the same name, the new account inherits the exposure, a `user_id` entry never does. |
| `filter.include_domains` / `exclude_domains` | Whole domains |
| `filter.include_entities` / `exclude_entities` | Single entity IDs |
| `filter.include_entity_globs` / `exclude_entity_globs` | Wildcards such as `sensor.*_temperature` |
| `entity_config.<entity_id>.name` | Name the app shows for the entity instead of the Home Assistant name, until the user renames it in the app. Under `users[]` it overrides the global one for that user. It does not share the entity; the filter decides that. |

Rules:

- **Deny by default.** A user who is not configured (in the UI or in YAML) sees no entities. A listed user without any `include_*` rule also sees none.
- An explicit exclude beats an include, as in the HomeKit Bridge.
- Wildcards must look like `domain.pattern` (for example `sensor.*_humidity`), in YAML, in the UI and in the import.
- Each user may appear only once in `configuration.yaml`; if two entries refer to the same user (by `username` or `user_id`), the first is used and a *Repairs* issue (`HAB-CFG-003`) names the user. A user in YAML and in the UI is fine: the YAML entry wins.
- Only `switch`, `sensor`, `binary_sensor` and `climate` entities are ever shared, whatever the filter says. Binary sensors (doors, windows, motion, presence) reveal whether someone is home, so prefer including single entities over the whole domain.
- New entities that match a filter (for example via a glob) are shared automatically.
- After editing the configuration, run the action **`haac_bridge.reload`** (admin only) or restart Home Assistant. Configuration problems appear under *Settings → Repairs*.

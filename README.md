# HAAC Bridge

Home Assistant custom integration that gives the **HA Android Client (HAAC)** a filtered, per-user view of your entities. Which entities each Home Assistant user sees in the app is configured in `configuration.yaml`, with the same filter syntax as the HomeKit Bridge.

> This project is not affiliated with or endorsed by Home Assistant, the Open Home Foundation or Nabu Casa.

- Requires Home Assistant **2026.9.0** or newer.
- Supported entity domains in v1: `switch`, `sensor`, `climate`.
- App: [stacknoise/haac-android](https://github.com/stacknoise/haac-android)

## Installation (HACS)

1. In HACS, open *Custom repositories* and add `https://github.com/stacknoise/haac-bridge` with category **Integration**.
2. Install **HAAC Bridge** and restart Home Assistant.
3. Add the configuration below to `configuration.yaml` and restart once more.

## Configuration

```yaml
haac_bridge:
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
```

| Key | Meaning |
| --- | --- |
| `users[].username` / `users[].user_id` | The Home Assistant user. `user_id` survives renames and is preferred for production. |
| `filter.include_domains` / `exclude_domains` | Whole domains |
| `filter.include_entities` / `exclude_entities` | Single entity IDs |
| `filter.include_entity_globs` / `exclude_entity_globs` | Wildcards such as `sensor.*_temperature` |

Rules:

- **Deny by default.** A user who is not listed sees no entities. A listed user without any `include_*` rule also sees none.
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

The app talks to the bridge over Home Assistant's WebSocket API with commands prefixed `haac_bridge/`. Available in this version: `haac_bridge/info`, `haac_bridge/exposure/revision`, `haac_bridge/entities/list`. Errors carry a code `HAB-<AREA>-<NNN>`, listed in [docs/error-codes.md](docs/error-codes.md).

## Development

Read [CLAUDE.md](CLAUDE.md) and [docs/concept.md](docs/concept.md) (chapters 10, 11, 13 and 18) first.

```bash
pip install -r requirements_test.txt -r requirements_lint.txt   # Python 3.14
pytest
ruff check . && ruff format --check .
bandit -c pyproject.toml -r custom_components scripts
python scripts/code_index.py          # regenerate docs/code-index.md and docs/error-codes.md
```

## License

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE).

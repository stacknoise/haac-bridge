# Client Bridge – HACS integration for HAAC (repo: stacknoise/haac-bridge)

Home Assistant custom integration (domain `client_bridge`) that gives the HA Android Client (HAAC, repo `stacknoise/haac-android`) a filtered, per-user view of HA entities over dedicated WebSocket commands. Exposure is configured per HA user in `configuration.yaml`, similar to the HomeKit Bridge filter syntax. Distributed via HACS.

## Source of truth

- `docs/concept.md` is the full specification shared with the app repo. Image links in it (mockups, icons) point to files that exist only in `stacknoise/haac-android`. Read the chapter that matches the task before writing code.
- Relevant chapters: 10 (integration structure, YAML, runtime), 11 (WebSocket API `client_bridge/*`, versioning), 13 (security), 14.2 (tests), 16 (GitHub, CI, releases). Chapters 3–9 and 15 describe the app and are context only.
- Items in concept 14.5 ("Open points") are undecided. Ask, or implement behind a clearly marked TODO.
- The integration name and domain are working titles (14.5); keep the domain `client_bridge` until decided.

## Repository layout

```text
CLAUDE.md
README.md                 # HACS installation, YAML example (concept 10.2)
hacs.json
docs/concept.md
custom_components/client_bridge/
  __init__.py  manifest.json  const.py  exposure.py  websocket.py  history.py  services.yaml
tests/
.github/workflows/        # validate.yml, tests.yml, release.yml (concept 16.5)
LICENSE  NOTICE           # Apache-2.0 (concept 16.2)
```

## Non-negotiable rules

- Resolve the caller only from `connection.user`; never accept a user name or id from the client (10.3).
- Deny by default: a HA user not listed in the YAML sees no entities.
- Only domains `switch`, `sensor`, `climate` are ever returned in v1, regardless of the filter.
- `client_bridge/call_service` executes only if the `entity_id` is exposed to the caller and the service belongs to the entity's domain; the bridge sets the target itself (11.4).
- History and statistics are filtered with the same exposure before querying the recorder.
- A breaking change of any `client_bridge/*` command raises `api_version` and the major version (16.4).

## Conventions

- Python for the HA version stated in `hacs.json`; use HA's `entityfilter` helper and a `voluptuous` config schema; async code only.
- Must pass `hassfest`, HACS validation (`hacs/action`), `ruff`, `bandit`.
- Tests with `pytest-homeassistant-custom-component`, covering the cases in concept 14.2.
- `manifest.json` version equals the release tag `vX.Y.Z`; Conventional Commits; protected `main`.
- License: Apache-2.0 (concept 16.2). No license headers in source files; dependencies only under Apache-2.0-compatible licenses.

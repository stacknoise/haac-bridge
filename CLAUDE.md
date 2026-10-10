# HAAC Bridge – HACS integration for HAAC (repo: stacknoise/haac-bridge)

Home Assistant custom integration (domain `haac_bridge`) that gives the HA Android Client (HAAC, repo `stacknoise/haac-android`) a filtered, per-user view of HA entities over dedicated WebSocket commands. Exposure is configured per HA user in the HA UI (options flow) or in `configuration.yaml`, similar to the HomeKit Bridge filter syntax. Distributed via HACS.

## Source of truth

- `docs/concept.md` is the full specification shared with the app repo. It is a copy: the leading version lives in `stacknoise/haac-android`; change it there first and take the file over unchanged (`docs/development.md` section 9). Image links in it (mockups, icons) point to files that exist only in `stacknoise/haac-android`. Read the chapter that matches the task before writing code.
- Relevant chapters: 10 (integration structure, YAML, runtime), 11 (WebSocket API `haac_bridge/*`, versioning), 13 (security), 14.2 (tests), 16 (GitHub, CI, releases), 18 (development guidelines for the bridge). Chapters 3–9 and 15 describe the app and are context only.
- Items in concept 14.5 ("Open points") are undecided. Ask, or implement behind a clearly marked TODO.
- Integration name "HAAC Bridge", domain `haac_bridge` (final). Minimum Home Assistant version 2026.9.0, declared in `hacs.json` (`"homeassistant": "2026.9.0"`) and respected in `manifest.json`.

## Repository layout

```text
CLAUDE.md
README.md                 # HACS installation, YAML example (concept 10.2)
hacs.json
docs/concept.md
docs/development.md       # developer guide: setup, checks, factories, error codes, code index, releases
docs/code-index.md        # GENERATED: every module, class and function with a one-line summary (concept 18.5)
docs/error-codes.md       # GENERATED: every HAB error code (concept 18.3)
scripts/code_index.py     # generator for the two files above
custom_components/haac_bridge/
  __init__.py  config_flow.py  manifest.json  const.py  services.yaml
  translations/en.json    # user texts of exceptions, issues and the config/options flow
  core/  config/  exposure/  entities/  services/  history/  areas/  instance/  schedules/  api/   # modules by topic (concept 18.1)
tests/                    # same topic structure
.github/workflows/        # validate.yml, tests.yml, release.yml (concept 16.5)
LICENSE  NOTICE           # Apache-2.0 (concept 16.2)
```

## Development rules (concept 18) – follow for every change

**Before writing code**
1. Read `docs/code-index.md` and search it for a function or class with the same purpose. Reuse or extend it; never write a second implementation of the same task.
2. Code needed in a second place is extracted into its own function right away: in the topic module, or in `core/` if several topics need it.

**Modules by topic (18.1)**
- One subpackage per topic under `custom_components/haac_bridge/`. `api/` only parses requests and calls topic modules; no business logic there.

**Factories (18.2)**
- Filters, entity descriptors, service calls, WebSocket replies and errors are created only by `FilterFactory`, `DescriptorFactory`, `ServiceCallFactory`, `ResponseFactory`, `ErrorFactory`. They are created in `async_setup` and stored in `hass.data[DOMAIN]`.
- Never branch on the entity domain to build descriptors or service calls outside a factory.

**Errors (18.3, 18.4)**
- Every raised exception is a `HaacBridgeError` subclass (derived from `HomeAssistantError`, with `translation_domain="haac_bridge"` and a `translation_key`) carrying an `ErrorCode`.
- All codes live only in `core/errors.py`, format `HAB-<AREA>-<NNN>`. A new error gets the next free number of its area; codes are never reused or renumbered. Add its user text to `translations/en.json` (section `exceptions`): short, plain language, no technical terms, no tokens, no trailing period (HA strips it).
- Every `haac_bridge/*` command runs inside the command wrapper in `core/command.py`, which converts exceptions via `ErrorFactory` and replies with `connection.send_error(msg_id, <HAB code>, <message>)`.
- No bare `except:` and no `except Exception` outside that wrapper. Never catch `asyncio.CancelledError`. Log every error once with its code.
- Configuration errors (`HAB-CFG-*`) also create an issue in Home Assistant Repairs; it is removed after a successful reload.
- When adding a HAB code that reaches the app, update the HAB → HAAC mapping table in concept 18.3.

**Code index (18.5)**
- Every module, class and function, including private ones, has a one-line docstring summary.
- After adding, renaming or removing a class or function, run `python scripts/code_index.py` and commit the regenerated `docs/code-index.md` and `docs/error-codes.md` in the same commit. Never edit them by hand. CI (`--check`, CPD) fails otherwise.

## Non-negotiable rules

- Resolve the caller only from `connection.user`; never accept a user name or id from the client (10.3).
- Deny by default: a HA user not configured (YAML or UI) sees no entities. YAML entries win over UI entries for the same user (10.2).
- Only domains `switch`, `sensor`, `climate` are ever returned in v1, regardless of the filter.
- `haac_bridge/call_service` executes only if the `entity_id` is exposed to the caller and the service and its `service_data` keys are in `const.ALLOWED_SERVICES` (table in concept 11.4); the bridge sets the target itself and calls with `SERVICE_TIMEOUT`. A change of the list also changes that table.
- History and statistics are filtered with the same exposure before querying the recorder, and stay within the limits of `const.py` (`TimeRange.check_length`, 10.3).
- Entities of the platform `haac_bridge` are never exposed (`exposure/own_entities.py`).
- Every state that reaches the app (list, events, history) goes through `entities/attributes.py` (`shareable_state`, `compressed_state`), so hidden attributes are never sent (11.3).
- `Exposure` caches its answers. A new input to an exposure decision needs an `async_invalidate_*` call where that input changes (`_async_follow_exposure_inputs` in `__init__.py`).
- A breaking change of any `haac_bridge/*` command raises `api_version` and the major version (16.4).

## Conventions

- Python version required by Home Assistant 2026.9 (>= 3.14.2; CI uses 3.14); use HA's `entityfilter` helper and a `voluptuous` config schema; async code only.
- Keep the sources parseable by older Python for `scripts/code_index.py` (no `type X = ...` statements; use plain alias assignments).
- Test and lint dependencies are pinned in `requirements_test.txt` (pytest-homeassistant-custom-component for the minimum HA version) and `requirements_lint.txt`; tool settings live in `pyproject.toml`.
- Must pass `hassfest`, HACS validation (`hacs/action`), `ruff` (incl. pydocstyle and complexity rules), `bandit`, PMD CPD (fails from 100 duplicated tokens) and `python scripts/code_index.py --check`.
- Tests with `pytest-homeassistant-custom-component`, covering the cases in concept 14.2.
- `manifest.json` version equals the release tag `vX.Y.Z`; Conventional Commits; protected `main`.
- License: Apache-2.0 (concept 16.2). No license headers in source files; dependencies only under Apache-2.0-compatible licenses.

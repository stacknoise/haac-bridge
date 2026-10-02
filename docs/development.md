# Developer guide – HAAC Bridge

This guide is for people (and coding agents) who change the integration in `stacknoise/haac-bridge`. It explains how the integration is built and checked, and the rules every change has to follow: modules by topic, the factory pattern, error codes, the generated code index and the CI checks.

It is a practical summary. The specification is [concept.md](concept.md); the rules below are concept chapters 16 and 18 (the integration itself is chapter 10, the WebSocket API chapter 11, schedules chapter 19). If this guide and the concept disagree, the concept wins. [CLAUDE.md](../CLAUDE.md) is the short version for coding agents.

The Android app lives in `stacknoise/haac-android` and has its own guide ([development.md there](https://github.com/stacknoise/haac-android/blob/main/docs/development.md)). Image links in `concept.md` point to files that exist only in that repository.

## 1. Get started

Requirements:

- Python **3.14.2 or newer** (Home Assistant 2026.9 requires it; CI uses 3.14). Minimum Home Assistant version: **2026.9.0** (`hacs.json`, `manifest.json`).
- Home Assistant does not run on Windows (it needs `fcntl`), so the **tests do not run on a Windows machine**. Run `pytest` on Linux, in WSL or in a container, or rely on CI. Lint and the code index run everywhere.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt    # pytest-homeassistant-custom-component, pinned to the minimum HA version
pip install -r requirements_lint.txt    # ruff, bandit
```

Checks (all of them run in CI and must pass before a pull request is merged):

```bash
ruff check .                              # lint, incl. pydocstyle and complexity
ruff format --check .                     # formatting (ruff format . fixes it)
bandit -c pyproject.toml -r custom_components scripts
python scripts/code_index.py --check      # code index and error code list up to date, docstrings present
pytest                                    # needs Linux/WSL/container
```

Besides these, CI runs `hassfest`, the HACS validation (`hacs/action`), PMD CPD (copy-paste detection) and CodeQL.

## 2. Project layout

```text
custom_components/haac_bridge/
  __init__.py  config_flow.py  const.py  manifest.json  services.yaml
  sensor.py  switch.py            # HA entities of the schedules (device "HAAC Schedules")
  translations/en.json            # texts of exceptions, issues, config and options flow
  core/        errors.py, error_factory.py, response_factory.py, command.py, caller.py, runtime.py
  config/      YAML schema, UI users (options flow), resolving users, Repairs issues
  exposure/    FilterFactory, per-user exposed set, revision hash, own entities
  entities/    DescriptorFactory, state subscription
  services/    ServiceCallFactory (validated service calls)
  history/     filtered history and statistics
  areas/       areas and floors catalog (import into the app)
  instance/    instance id and addresses for haac_bridge/info
  schedules/   model, store, triggers, planner, runner, manager, entities (concept 19)
  api/         the haac_bridge/* WebSocket commands, one module per command group
scripts/code_index.py             # generates docs/code-index.md and docs/error-codes.md
tests/                            # same topic structure as the integration
docs/                             # concept.md, code-index.md, error-codes.md
.github/workflows/                # validate.yml, tests.yml, release.yml
```

### Modules by topic (concept 18.1)

- One subpackage per topic. A module belongs to exactly one topic; code used by several topics moves to `core/`.
- **`api/` only parses requests and calls the topic modules.** It contains no business logic.

### How a request flows

```text
app ──WebSocket──▶ HA websocket_api ──▶ command wrapper (core/command.py)
                                           │ validates the request fields (voluptuous)
                                           │ runs the handler in api/<group>.py
                                           ▼
                                        topic module (exposure, services, history, schedules, …)
                                           │
   result / error reply ◀── ResponseFactory ◀── ErrorFactory (on any exception)
```

The caller is always `connection.user`; the bridge never accepts a user name or id from the client. A user who is not configured sees nothing (deny by default).

`HaacBridgeData` (`core/runtime.py`) holds the factories, the current exposure, the user entries and the schedule manager. `async_setup` creates it once and stores it in `hass.data` under `DATA_KEY`; get it with `get_data(hass)`.

## 3. Adding or changing a command

1. Add the handler to the module of its group in `api/` (or a new module for a new group), declared with the decorator:

   ```python
   @bridge_command("haac_bridge/areas")          # optional second argument: the request fields (voluptuous)
   async def ws_areas(
       hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
   ) -> dict[str, Any]:
       """Return the HA floors and areas that hold entities exposed to the caller."""
       snapshot = get_data(hass).exposure.snapshot(hass, require_user(connection))
       return area_catalog(hass, snapshot.entity_ids)   # topic module; plain, JSON-serialisable payload
   ```

   (From `api/areas.py`. The caller comes from `require_user(connection)`.)

2. Add the handler to `COMMANDS` in `api/__init__.py`. `async_setup` registers every entry inside the command wrapper.
3. Return the payload, or raise a `HaacBridgeError`; never reply with `connection.send_*` yourself. A subscription returns `SubscriptionStarted(initial)`.
4. Write tests (section 8) and document the command in concept 11.2.
5. **API versioning:** a breaking change of any command raises `API_VERSION` in `const.py` and the major version of the integration (concept 16.4). A new optional feature is added to `FEATURES`; the app finds it in the `features` list of `haac_bridge/info`.

## 4. Factory pattern (concept 18.2)

**Rule:** filters, entity descriptors, service calls, schedule triggers, WebSocket replies and errors are created only by their factory. Outside a factory no code branches on the entity domain to build descriptors or service calls. A new domain is then added in one place.

Factories are plain classes created once in `async_setup` and stored in `HaacBridgeData`; tests replace them with fakes.

| Factory | File | Creates |
| --- | --- | --- |
| `FilterFactory` | `exposure/filter_factory.py` | one `EntityFilter` per HA user from the YAML or UI configuration |
| `DescriptorFactory` | `entities/descriptor_factory.py` | entity descriptor per domain (switch, sensor, climate) from an HA state |
| `ServiceCallFactory` | `services/call_factory.py` | validated service call (domain, service, data, target); enforces exposure and domain services |
| `TriggerFactory` | `schedules/triggers.py` | one trigger planner per `when.type` (`time`, `sunrise`, `sunset`) that computes the next run |
| `ResponseFactory` | `core/response_factory.py` | WebSocket result, error and event replies |
| `ErrorFactory` | `core/error_factory.py` | `HaacBridgeError` from any caught exception |

Adding a factory (or a kind to one): implement it in its topic module, create it in `async_setup`, add it to `HaacBridgeData`, test the cases per type, and add it to the table in concept 18.2 and to the code index (section 6).

## 5. Error codes (concept 18.3, 18.4)

Every error of the bridge is a `HaacBridgeError` (derived from Home Assistant's `HomeAssistantError`) with an `ErrorCode`.

- **All codes are defined in one file:** `custom_components/haac_bridge/core/errors.py`. Nowhere else.
- Format `HAB-<AREA>-<NNN>`. Areas: `CFG` YAML configuration, `AUTH` caller, `SVC` service calls, `ENT` entities, `HIST` history and statistics, `SCH` schedules, `WS` request format, `INT` unexpected errors. A code is never reused or renumbered.
- `docs/error-codes.md` is **generated** from `core/errors.py` and `translations/en.json`. Look codes up there; never edit it by hand.
- Exception classes by area: `ConfigError`, `NotAllowedError`, `InvalidServiceError`, `EntityNotFoundError`, `HistoryError`, `ScheduleError`, `RequestError`, `InternalError`. Each has a `default_code`; a more specific code is passed in: `raise ScheduleError(ErrorCode.SCH_NOT_FOUND)`.

**Adding an error code**

1. Take the next free number of the area and add a member to `ErrorCode`. The **docstring below the member** is its technical description (the generator reads it):

   ```python
   SCH_LIMIT = "HAB-SCH-005"
   """The user already has the maximum number of schedules."""
   ```

2. Add the user text to `translations/en.json`, section `exceptions`, under the lowercase member name (`sch_limit`). Short, plain language, no technical terms, no entity attributes or tokens, **no trailing period** (Home Assistant strips it).
3. Add the member to `APP_CODES` in `core/errors.py`: the HAAC code the app shows for it, or `None` if only the HA administrator sees it (Repairs).
4. If the code reaches the app, update the HAB → HAAC table in concept 18.3 and `DefaultErrorFactory.BRIDGE_CODES` in the app repository (unknown HAB codes show as `HAAC-BRG-005` there).
5. Run `python scripts/code_index.py` and commit `docs/error-codes.md`.
6. `tests/core/test_errors.py` checks that codes are unique, well-formed, translated and mapped. It must stay green.

**Rules**

- No bare `except:` and no `except Exception` outside the command wrapper (`core/command.py`); that is the only place where `BLE001` is allowed. Never catch `asyncio.CancelledError`.
- Every error is logged **once** with its code (the wrapper does it for commands), never with tokens or passwords.
- `HAB-CFG-*` errors also create an issue in Home Assistant Repairs with code and explanation; it disappears after a successful `haac_bridge.reload`.
- `HAB-SCH-002` is a run result (`last_run.code`), not a command reply.

## 6. Code index (concept 18.5)

`docs/code-index.md` lists **every module, class and function** of the integration with signature, file and a one-line summary, grouped by topic. It exists so that existing code is found and reused instead of written again.

- **Before writing code**, search `docs/code-index.md` for a function or class with the same purpose. Reuse or extend it.
- Every module, class and function, including private ones, has a **one-line docstring summary** (Google style; `ruff` enforces pydocstyle).
- After adding, renaming or removing a symbol, or after changing a docstring or a signature: `python scripts/code_index.py`, and commit the regenerated `docs/code-index.md` and `docs/error-codes.md` **in the same commit**. CI (`--check`) fails otherwise.
- Never edit the files by hand. After a merge or rebase conflict in `docs/code-index.md`, regenerate it.
- The generator reads the sources with Python's `ast` module and runs without Home Assistant. `ast.unparse` renders some code differently between Python versions (for example `lambda: None`), so **run it with Python 3.14**, the version CI uses. Keep the sources parseable by older versions (no `type X = …` statements; use plain alias assignments).

## 7. No duplicate code and code style (concept 18.6)

- Code needed in a second place is extracted into its own function right away, in the topic module or in `core/`.
- CI runs PMD CPD over `custom_components` and `scripts` and fails from **100 duplicated tokens**.
- `ruff` rules (`pyproject.toml`): line length 100, Google docstrings, McCabe complexity at most 10, isort with `force-sort-within-sections`, bandit (`S`) rules, async pitfalls (`ASYNC`), blind-except (`BLE`). Tests are exempt from docstring and assert rules.
- Async code only; use Home Assistant's `entityfilter` helper and a `voluptuous` schema for the configuration.
- `manifest.json` has `single_config_entry`; the config entry is needed for the entities of the schedules. A YAML-only setup gets it through the import flow.

## 8. Tests

- `pytest` with `pytest-homeassistant-custom-component`, `asyncio_mode = "auto"`, tests under `tests/` in the same topic structure as the integration. The cases that must be covered are listed in concept 14.2.
- `tests/conftest.py` offers the fixtures to start from: `add_user` (a HA user, optionally an admin), `access_token_for` and `client_for` (a WebSocket client signed in as a given user). Test commands through that client, so the whole wrapper, schema and exposure are exercised.
- Put fakes used by several test files into a shared module or `conftest.py`; CPD also checks the tests.
- The tests of this repository do not run on Windows (section 1); CI runs them on Linux.

## 9. Git, pull requests and CI

- `main` is protected by rulesets: changes only by pull request, squash merge only, linear history, no force push or deletion, required checks: HACS validation, `hassfest`, ruff/bandit/code index, CPD, pytest, CodeQL.
- Branches `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`; commit messages and PR titles follow Conventional Commits. Start every branch from the current `origin/main`.
- After a squash merge, a second PR that was built on the first one needs `git rebase --onto origin/main <last commit of the first branch> <second branch>` and a push with `--force-with-lease`.
- Workflows: `validate.yml` (hassfest, HACS validation; also nightly), `tests.yml` (lint job, CPD job, pytest), `release.yml`.

### The concept document

`docs/concept.md` here is a **copy**. The leading version is `docs/concept.md` in `stacknoise/haac-android`. After a change there has been merged, take the file over into this repository in its own pull request (the blob must be identical). Do not edit the copy here first.

## 10. Versions and releases

- The version is in `custom_components/haac_bridge/manifest.json` (`version`) and `pyproject.toml`; both are raised together, in their own pull request (`chore(release): bump the version to X.Y.Z`).
- Tag the merge commit `vX.Y.Z` and push the tag. `release.yml` checks that the `manifest.json` version equals the tag and creates the GitHub Release with generated notes; HACS reads the releases.
- Tags `v*` are protected (no deleting, moving or overwriting), so check the version on `main` before tagging.
- Semantic versioning: a breaking change of a WebSocket command raises `API_VERSION` and the major version; new optional features raise the minor version and extend `FEATURES`.
- Existing installations update through HACS (⋮ → Redownload) and a restart of Home Assistant.

## 11. Non-negotiable rules

- Resolve the caller only from `connection.user`; never accept a user name or id from the client.
- Deny by default: a HA user who is not configured (YAML or UI) sees no entities. A YAML entry wins over a UI entry for the same user.
- Only the domains `switch`, `sensor` and `climate` are ever returned in v1, whatever the filter says. Entities of the platform `haac_bridge` itself are never exposed.
- `haac_bridge/call_service` executes only if the `entity_id` is exposed to the caller and the service belongs to the entity's domain; the bridge sets the target itself.
- History and statistics are filtered with the same exposure before the recorder is queried.
- Schedules check owner and exposure on every run, with the rights of the owner (concept 19.3).
- No tokens or passwords in logs. No license headers in source files; dependencies only under Apache-2.0-compatible licenses.

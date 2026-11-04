# WebSocket API

Back to the [README](../README.md). This page is for developers; you do not need it to use HAAC Bridge.

The app talks to the bridge over Home Assistant's WebSocket API with commands prefixed `haac_bridge/`. Errors carry a code `HAB-<AREA>-<NNN>`, listed in [error-codes.md](error-codes.md).

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

The schedule commands are `haac_bridge/schedules/revision`, `list`, `create`, `update`, `delete` and `run_now` and `haac_bridge/subscribe_schedules` (event `{"schedules_changed": {"revision": …}}`). `update`, `delete` and `run_now` name the schedule with `schedule_id`; `run_now` replies as soon as the run has started, its result follows as `last_run` with `schedules_changed`, and the same schedule can be run by hand again after 10 seconds (`HAB-SCH-007`); `update` also needs the `updated_at` of the version that was edited (`HAB-SCH-004` if it changed in the meantime). Every schedule in `list`, `create` and `update` replies carries `own`, which is true if the caller is the owner (the app uses it to tell its own schedules from foreign ones in the administrator scope). `haac_bridge/schedules/preview` (`when`, `repeat`) returns the next runs of a draft and `haac_bridge/schedules/runs` (`log_id`?, `after_seq`?) the caller's run log entries after a cursor; `haac_bridge/schedules/skip_run` (`schedule_id`, `date`, `skip`) skips the run of one date of a repeating schedule or takes it up again (`HAB-SCH-010` if the date is not one of the next runs or no run would be left; schedules carry `skipped_dates` and `upcoming_runs`); `haac_bridge/entities/set_disabled` (`entity_id`, `disabled`) deactivates or activates an entity for the caller (event `disabled_changed`). `haac_bridge/info` lists `features: ["schedules", "entity_disable", "schedule_repeat", "schedule_runs", "client_info", "schedule_skip"]`. Regular users see only their own schedules, administrators all of them (`scope`). See concept chapter 19 and [error-codes.md](error-codes.md) for the `HAB-SCH-*` codes.

History and statistics only include requested entities that are exposed to the caller; others are left out silently. Times are ISO 8601; a period in the future returns an empty result.

The bridge sets the service target itself and runs the call in the context of the signed-in user.

The app uses `instance_id` to recognise the same Home Assistant under different addresses and switches between the internal and the external address automatically. Set the addresses under *Settings → System → Network* in Home Assistant.

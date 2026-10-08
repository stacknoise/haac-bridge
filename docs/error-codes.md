# Error codes – HAAC Bridge

> GENERATED FILE – do not edit by hand. Regenerated from `core/errors.py` and `translations/en.json` with `python scripts/code_index.py` (concept 18.3, 18.5).

Every error of the integration carries one of these codes (format `HAB-<AREA>-<NNN>`). The app shows its own HAAC code and the HAB code in the error details.

| Code | Message | Shown in the app as | Technical description |
| --- | --- | --- | --- |
| HAB-CFG-001 | The haac_bridge configuration in configuration.yaml is invalid | – (HA admin, Repairs) | The haac_bridge section in configuration.yaml failed schema validation on reload. |
| HAB-CFG-002 | A user in the haac_bridge configuration does not exist in Home Assistant | – (HA admin, Repairs) | A `username` or `user_id` in the configuration matches no Home Assistant user. |
| HAB-AUTH-001 | The request has no signed-in Home Assistant user | HAAC-AUTH-003 | The WebSocket connection has no Home Assistant user bound to its access token. |
| HAB-AUTH-002 | Your Home Assistant user is deactivated | HAAC-AUTH-006 | The Home Assistant user bound to the connection is deactivated. |
| HAB-SVC-001 | You are not allowed to control this device | HAAC-BRG-003 | The target entity is not exposed to the calling user. |
| HAB-SVC-002 | This action is not available for this device | HAAC-BRG-004 | The requested service does not belong to the domain of the target entity. |
| HAB-SVC-003 | Home Assistant could not carry out the action | HAAC-BRG-005 | Home Assistant raised an error while executing an allowed service call. |
| HAB-ENT-001 | This device no longer exists in Home Assistant | HAAC-ENT-001 | The requested entity does not exist in the state machine. |
| HAB-HIST-001 | History is not available on this server | HAAC-BRG-006 | Recorder or history is not loaded, or the query against it failed. |
| HAB-HIST-002 | The chosen period is too long | HAAC-BRG-006 | The requested history or statistics period is longer than the bridge allows. |
| HAB-SCH-001 | The schedule is not valid | HAAC-SCH-003 | A schedule failed validation (name, time, days, action or entities). |
| HAB-SCH-002 | A device could not be switched by the schedule | HAAC-SCH-007 | A schedule run could not switch an entity (not exposed, unavailable or not permitted). |
| HAB-SCH-003 | This schedule does not exist | HAAC-SCH-001 | The schedule does not exist. |
| HAB-SCH-004 | The schedule was changed in the meantime | HAAC-SCH-004 | The schedule changed after the caller loaded it (optimistic concurrency). |
| HAB-SCH-005 | You have reached the limit of schedules | HAAC-SCH-005 | The user already has the maximum number of schedules. |
| HAB-SCH-006 | You are not allowed to change this schedule | HAAC-SCH-006 | A regular user touched a foreign schedule, or an admin tried to change a foreign entity list. |
| HAB-WS-001 | The request could not be understood | HAAC-BRG-005 | The request fields of a haac_bridge/* command failed validation. |
| HAB-INT-000 | Something went wrong in HAAC Bridge | HAAC-BRG-005 | An exception without a HAB code reached the command wrapper. |

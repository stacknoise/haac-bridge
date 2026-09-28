# Error codes – HAAC Bridge

> GENERATED FILE – do not edit by hand. Regenerated from `core/errors.py` and `translations/en.json` with `python scripts/code_index.py` (concept 18.3, 18.5).

Every error of the integration carries one of these codes (format `HAB-<AREA>-<NNN>`). The app shows its own HAAC code and the HAB code in the error details.

| Code | Message | Shown in the app as | Technical description |
| --- | --- | --- | --- |
| HAB-CFG-001 | The haac_bridge configuration in configuration.yaml is invalid. | – (HA admin, Repairs) | The haac_bridge section in configuration.yaml failed schema validation on reload. |
| HAB-CFG-002 | A user in the haac_bridge configuration does not exist in Home Assistant. | – (HA admin, Repairs) | A `username` or `user_id` in the configuration matches no Home Assistant user. |
| HAB-AUTH-001 | The request has no signed-in Home Assistant user. | HAAC-AUTH-003 | The WebSocket connection has no Home Assistant user bound to its access token. |
| HAB-SVC-001 | You are not allowed to control this device. | HAAC-BRG-003 | The target entity is not exposed to the calling user. |
| HAB-SVC-002 | This action is not available for this device. | HAAC-BRG-004 | The requested service does not belong to the domain of the target entity. |
| HAB-SVC-003 | Home Assistant could not carry out the action. | HAAC-BRG-005 | Home Assistant raised an error while executing an allowed service call. |
| HAB-ENT-001 | This device no longer exists in Home Assistant. | HAAC-ENT-001 | The requested entity does not exist in the state machine. |
| HAB-HIST-001 | History is not available on this server. | HAAC-BRG-006 | Recorder or history is not loaded, or the query against it failed. |
| HAB-WS-001 | The request could not be understood. | HAAC-BRG-005 | The request fields of a haac_bridge/* command failed validation. |
| HAB-INT-000 | Something went wrong in HAAC Bridge. | HAAC-BRG-005 | An exception without a HAB code reached the command wrapper. |

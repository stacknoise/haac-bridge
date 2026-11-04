# Features in detail

Back to the [README](../README.md). This page lists everything HAAC Bridge does, including the technical details.

**Sharing entities per user**
- Choose, per Home Assistant user, which entities the app may show and control: whole domains, single entities and wildcards such as `sensor.*_humidity`, each to include or to exclude. An explicit exclusion always wins, as in the HomeKit Bridge (the filter is built with Home Assistant's own `entityfilter` helper).
- **Deny by default:** a user who is not configured, or has no include rule, sees nothing. Only `switch`, `sensor`, `binary_sensor` and `climate` are ever shared, whatever the filter says.
- Configure it in the **Home Assistant UI** (config and options flow, changes apply at once) or in `configuration.yaml`, or both; YAML entries win for a user who is in both. Users are identified by login name or by the stable user ID.
- Optional display names per entity, global or per user; the app shows them until the user renames the entity locally. A name never shares an entity by itself.
- New entities that match a filter are shared automatically, and connected apps are told at once (`exposure_changed`), also after a configuration change.

**Deactivating entities**
- Each user can deactivate a shared entity in the app. It then stays visible but cannot be controlled: `call_service` refuses it (`HAB-ENT-002`) and the user's own schedules that use it are switched off (`HAB-SCH-008` if one is switched on again by hand). Activating the entity switches those schedules on again. The list is kept per user in `.storage/haac_bridge.disabled_entities`.

**What the app can do through the bridge**
- Read the shared entities with their current state, and follow their live changes. Attributes that name other entities (for example the members of a group) or carry an access link are left out.
- Call services on shared entities only: the entity must be shared with the caller, the service must be on the bridge's short list for the entity's domain (the ones the app uses, see concept 11.4), and the bridge sets the target itself, so a client cannot add other targets. A call that takes longer than 15 seconds counts as failed.
- Read history and long-term statistics of shared entities only, filtered before the recorder is queried; at most 50 entities per request, up to 366 days of history, 32 days of hourly and 5 years of daily statistics.
- Read the Home Assistant floors and areas that hold shared entities, so the app can offer an import of levels and rooms (no entity IDs are sent).
- Report the Home Assistant version, the bridge and API version, the instance ID and the internal, external and cloud address, so the app can recognise the same Home Assistant under different addresses.

**Schedules (time-controlled actions)**
- Users create schedules in the app, for example "every weekday at 06:45 turn the light on". A schedule switches `switch` entities (turn on, turn off or toggle) at a fixed time on chosen weekdays, or at sunrise or sunset with an offset of up to 3 hours.
- Schedules are stored and run **by the bridge**, so they work with the app closed, the phone off or on another network. They run in the context of their owner, so the logbook shows who triggered them (a manual run in the context of the user who started it), and at every run the bridge checks again that the owner still exists and may see each entity.
- A schedule can run **once** (then it deletes itself) or **repeat** daily, weekly, monthly or yearly with an interval and an optional end date; after the last run it is deleted. A single run of a repeating schedule can be **skipped** (for example a public holiday); the schedule keeps its rules and the bridge just leaves that date out (`skip_run`). The app can preview the next runs, and a schedule can opt in to a message in the app for each run (`notify`), which the bridge keeps in a short **run log**.
- Each schedule appears in Home Assistant as an *enabled* switch and a *next run* timestamp sensor on the device **HAAC Schedules**, named after the schedule and its owner, for example *Wake up (Anton)*, so equal names of two users stay apart. Turning the switch off pauses the schedule. These entities are never shared with app users, whatever a filter says.
- Home Assistant administrators see and manage all schedules in the app; the entity list of a foreign schedule can only be changed by its owner.
- Schedules follow the users: they are deleted at once when their owner is removed from the bridge configuration or deleted in Home Assistant, and paused while the owner is deactivated. Removing the integration deletes all schedules; while it is disabled or reloading, schedules are kept and wait.
- Schedules need the integration to have a configuration entry. If you configure the bridge in `configuration.yaml` only, it adds the entry by itself. Schedules are saved in `.storage/haac_bridge.schedules`, which a full Home Assistant backup includes.
- Times are Home Assistant's local time. A time that does not exist on the day the clocks go forward runs at the first minute after the gap; a time that occurs twice runs once.

**Logging and the Activity page**
- The bridge writes what it does to the Home Assistant log (logger `custom_components.haac_bridge`): every switching action of a user (who, from which device, entity, service, data, result, duration), every schedule run (each switched entity and the result), changes of schedules, deactivated entities, configuration changes and the start of the integration. One line per action in the form `action=call_service user=Anton(1a2b3c4d) source=app client="Pixel 8" entity=switch.garage_socket service=turn_on result=ok ms=42`. Texts typed by users are escaped, so they cannot forge log lines. IP addresses and tokens are never logged.
- Every switching action through the bridge, successful or failed, also appears on the Home Assistant **Activity** page (logbook), for example *turned on via HAAC app (Pixel 8)* or *turned off by a schedule*, linked to the entity and to the user. Refused calls (not shared, not allowed) are only logged. The Activity page does not show schedule names.
- The **log level** is `warning` by default, which shows problems only. Set it to `info` to record every action, or to `debug` to log every request as well (noisy). Set it under *Configure → Logging* or in `configuration.yaml`; a value in the YAML wins. The Activity entries can be switched off there too.
- The bridge keeps no log of its own: the Home Assistant log and the recorder store everything, so the usual retention applies.

**Safety and operations**
- The caller is always the Home Assistant user behind the access token; the app cannot ask for another user's entities.
- Stable error codes (`HAB-…`) with plain-language messages, configuration problems and unknown users as *Repairs* issues, and the action `haac_bridge.reload` to re-read the YAML.
- Distributed through HACS; CI runs hassfest, HACS validation, ruff, bandit, CodeQL and the tests.

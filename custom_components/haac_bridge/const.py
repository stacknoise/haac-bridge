"""Constants shared by all topics of HAAC Bridge."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "haac_bridge"

API_VERSION: Final = 1
"""Version of the haac_bridge/* WebSocket API; raised on every breaking change (11.4)."""

SUPPORTED_DOMAINS: Final = ("climate", "sensor", "switch")
"""Entity domains returned in v1, regardless of the user's filter (10.2)."""

FEATURES: Final = ("schedules", "entity_disable")
"""Optional features this bridge offers; `haac_bridge/info` reports them to the app (11.2, 11.4)."""

CONF_USERS: Final = "users"
CONF_USERNAME: Final = "username"
CONF_USER_ID: Final = "user_id"
CONF_FILTER: Final = "filter"
CONF_ENTITY_CONFIG: Final = "entity_config"
CONF_NAME: Final = "name"
CONF_NAMES: Final = "names"

SERVICE_RELOAD: Final = "reload"

SIGNAL_EXPOSURE_CHANGED: Final = f"{DOMAIN}_exposure_changed"
"""Dispatcher signal sent after a reload replaced the exposure of all users."""

SIGNAL_SCHEDULES_CHANGED: Final = f"{DOMAIN}_schedules_changed"
"""Dispatcher signal sent after a schedule was created, changed, run, paused or removed (19.4)."""

SIGNAL_SCHEDULE_CHANGED: Final = f"{DOMAIN}_schedule_changed_{{}}"
"""Dispatcher signal of one schedule (format it with the schedule id); only its entities follow it."""

SCHEDULE_STORE_KEY: Final = f"{DOMAIN}.schedules"
"""Name of the storage file (in `.storage`) that holds the schedules (concept 19.2)."""

SCHEDULE_STORE_VERSION: Final = 1
"""Version of the schedule store; raised when the stored format changes."""

SCHEDULE_DOMAIN: Final = "switch"
"""The only entity domain a schedule can switch in v1 (concept 19.1)."""

MAX_SCHEDULES_PER_USER: Final = 50
MAX_ENTITIES_PER_SCHEDULE: Final = 20
MAX_NAME_LENGTH: Final = 60
MAX_OFFSET_MIN: Final = 180
"""Limits of a schedule (concept 19.2); the offset applies to sunrise and sunset in either direction."""

MAX_INTERVAL: Final[dict[str, int]] = {
    "daily": 365,
    "weekly": 52,
    "monthly": 12,
    "yearly": 1,
}
"""Largest `repeat.interval` per frequency; the smallest is 1 (concept 19.10). `once` has no interval."""

MAX_START_DATE_AHEAD: Final = timedelta(days=366)
"""How far in the future the date of a one-off schedule may lie (concept 19.10)."""

RUN_NOW_COOLDOWN: Final = 10
"""Seconds after a manual run during which run_now of the same schedule is refused (HAB-SCH-007)."""

RUN_RESULT_SAVE_DELAY: Final = 1
"""Seconds run results and system pauses wait before they are written, so a burst is one write."""

MISSED_RUN_GRACE: Final = timedelta(minutes=5)
"""A run that HA missed by at most this long is still carried out once at startup (concept 19.3)."""

SERVICE_TIMEOUT: Final = 15
"""Seconds a service call of the bridge may take before it counts as failed (HAB-SVC-003)."""

ALLOWED_SERVICES: Final[dict[str, dict[str, frozenset[str]]]] = {
    "switch": {
        "turn_on": frozenset(),
        "turn_off": frozenset(),
        "toggle": frozenset(),
    },
    "climate": {
        "turn_on": frozenset(),
        "turn_off": frozenset(),
        "set_hvac_mode": frozenset({"hvac_mode"}),
        "set_temperature": frozenset({"temperature", "target_temp_low", "target_temp_high"}),
        "set_humidity": frozenset({"humidity"}),
        "set_fan_mode": frozenset({"fan_mode"}),
        "set_preset_mode": frozenset({"preset_mode"}),
        "set_swing_mode": frozenset({"swing_mode"}),
        "set_swing_horizontal_mode": frozenset({"swing_horizontal_mode"}),
    },
    "sensor": {},
}
"""Services the bridge carries out per domain, each with the service_data keys it accepts (11.4).

Matches what the app and the schedules call; anything else, even if HA has it, is refused.
"""

MAX_HISTORY_ENTITIES: Final = 50
"""Most entities one history or statistics request may name (review finding S2)."""

MAX_HISTORY_PERIOD: Final = timedelta(days=366)
"""Longest period of haac_bridge/history; the app asks for states over any custom range."""

MAX_HOURLY_STATISTICS_PERIOD: Final = timedelta(days=32)
"""Longest period of hourly statistics; the app uses them up to 31 days (plus one lead period)."""

MAX_STATISTICS_PERIOD: Final = timedelta(days=5 * 366)
"""Longest period of daily, weekly or monthly statistics."""

TARGET_KEYS: Final = frozenset({"entity_id", "device_id", "area_id", "floor_id", "label_id"})
"""Keys that name a target; no entry of ALLOWED_SERVICES lists one, so the bridge alone sets the target (11.4)."""

DISABLED_STORE_KEY: Final = f"{DOMAIN}.disabled_entities"
"""Name of the storage file that holds the deactivated entities per user (concept 7.5)."""

DISABLED_STORE_VERSION: Final = 1
"""Version of the store of deactivated entities."""

MAX_DISABLED_PER_USER: Final = 500
"""Most entities one user can have deactivated (concept 7.5)."""

RUN_LOG_STORE_KEY: Final = f"{DOMAIN}.schedule_runs"
"""Name of the storage file that holds the run log of the schedules (concept 19.11)."""

RUN_LOG_STORE_VERSION: Final = 1
"""Version of the run log store."""

RUN_LOG_RETENTION: Final = timedelta(days=30)
"""How long a run log entry is kept (concept 19.11)."""

MAX_RUN_LOG_PER_OWNER: Final = 200
"""Most run log entries kept per owner; the oldest go first (concept 19.11)."""

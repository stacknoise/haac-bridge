"""Constants shared by all topics of HAAC Bridge."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "haac_bridge"

API_VERSION: Final = 1
"""Version of the haac_bridge/* WebSocket API; raised on every breaking change (11.4)."""

SUPPORTED_DOMAINS: Final = ("climate", "sensor", "switch")
"""Entity domains returned in v1, regardless of the user's filter (10.2)."""

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

MISSED_RUN_GRACE: Final = timedelta(minutes=5)
"""A run that HA missed by at most this long is still carried out once at startup (concept 19.3)."""

TARGET_KEYS: Final = frozenset({"entity_id", "device_id", "area_id", "floor_id", "label_id"})
"""Keys a client must not put into service_data; the bridge sets the target itself (11.4)."""

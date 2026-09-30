"""Constants shared by all topics of HAAC Bridge."""

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

TARGET_KEYS: Final = frozenset({"entity_id", "device_id", "area_id", "floor_id", "label_id"})
"""Keys a client must not put into service_data; the bridge sets the target itself (11.4)."""

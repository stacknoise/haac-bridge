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

SERVICE_RELOAD: Final = "reload"

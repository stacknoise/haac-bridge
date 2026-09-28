"""The haac_bridge/* WebSocket commands, one module per command group (concept 11.2)."""

from .entities import ws_entities_list
from .exposure import ws_exposure_revision
from .info import ws_info

COMMANDS = (ws_info, ws_exposure_revision, ws_entities_list)

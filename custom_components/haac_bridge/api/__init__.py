"""The haac_bridge/* WebSocket commands, one module per command group (concept 11.2)."""

from .areas import ws_areas
from .entities import ws_entities_list, ws_subscribe_entities
from .exposure import ws_exposure_revision
from .history import ws_history, ws_statistics
from .info import ws_info
from .schedules import (
    ws_schedules_create,
    ws_schedules_delete,
    ws_schedules_list,
    ws_schedules_revision,
    ws_schedules_run_now,
    ws_schedules_update,
    ws_subscribe_schedules,
)
from .services import ws_call_service

COMMANDS = (
    ws_info,
    ws_exposure_revision,
    ws_entities_list,
    ws_subscribe_entities,
    ws_call_service,
    ws_history,
    ws_statistics,
    ws_areas,
    ws_schedules_revision,
    ws_schedules_list,
    ws_schedules_create,
    ws_schedules_update,
    ws_schedules_delete,
    ws_schedules_run_now,
    ws_subscribe_schedules,
)

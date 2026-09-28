"""Recorder queries for haac_bridge/history and haac_bridge/statistics (concept 8.1, 8.3, 10.3).

Callers pass only entity IDs that already passed the exposure filter. Both queries run in the
recorder's executor, like Home Assistant's own history and statistics commands.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Any, Final

from homeassistant.components.recorder import get_instance, history, statistics
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.util.dt as dt_util
from sqlalchemy.exc import SQLAlchemyError
import voluptuous as vol

from ..core.errors import ErrorCode, HistoryError, RequestError

PERIODS: Final = ("hour", "day", "week", "month")
"""Statistic periods the app may request (concept 11.2)."""

STATISTIC_TYPES: Final = ("mean", "min", "max", "sum")
"""Statistic values the app may request (concept 11.2)."""


def utc_datetime(value: Any) -> datetime:
    """Voluptuous validator: parse an ISO 8601 string into an aware UTC datetime."""
    if isinstance(value, str) and (parsed := dt_util.parse_datetime(value)) is not None:
        return dt_util.as_utc(parsed)
    raise vol.Invalid("expected an ISO 8601 date and time")


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Requested period in UTC; `end` None means up to now."""

    start: datetime
    end: datetime | None

    def __post_init__(self) -> None:
        """Reject a period that ends before it starts (HAB-WS-001)."""
        if self.end is not None and self.end < self.start:
            raise RequestError(ErrorCode.WS_INVALID_REQUEST)

    @property
    def in_future(self) -> bool:
        """Return True if the period starts after now, so there is nothing recorded."""
        return self.start > dt_util.utcnow()


async def async_history(
    hass: HomeAssistant,
    entity_ids: list[str],
    period: TimeRange,
    minimal_response: bool,
) -> dict[str, list[dict[str, Any]]]:
    """Return significant state changes per entity in HA's compressed state format."""
    return await _async_run(
        hass,
        partial(
            history.get_significant_states,
            hass,
            period.start,
            period.end,
            entity_ids,
            None,
            include_start_time_state=True,
            significant_changes_only=True,
            minimal_response=minimal_response,
            no_attributes=False,
            compressed_state_format=True,
        ),
    )


async def async_statistics(
    hass: HomeAssistant,
    entity_ids: list[str],
    period: TimeRange,
    resolution: str,
    types: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """Return long-term statistics per entity; `start` and `end` of each row in milliseconds."""
    return await _async_run(
        hass, partial(_statistics_in_ms, hass, set(entity_ids), period, resolution, set(types))
    )


def _statistics_in_ms(
    hass: HomeAssistant,
    statistic_ids: set[str],
    period: TimeRange,
    resolution: Any,
    types: Any,
) -> dict[str, list[dict[str, Any]]]:
    """Query statistics in the executor and convert row timestamps to ms, as HA's own API does."""
    result: dict[str, list[dict[str, Any]]] = statistics.statistics_during_period(
        hass, period.start, period.end, statistic_ids, resolution, None, types
    )  # type: ignore[assignment]
    for rows in result.values():
        for row in rows:
            row["start"] = int(row["start"] * 1000)
            row["end"] = int(row["end"] * 1000)
    return result


async def _async_run(hass: HomeAssistant, query: Callable[[], Any]) -> Any:
    """Run a recorder query in its executor; database or recorder errors become HAB-HIST-001."""
    try:
        return await get_instance(hass).async_add_executor_job(query)
    except (SQLAlchemyError, HomeAssistantError) as err:
        raise HistoryError(ErrorCode.HIST_UNAVAILABLE) from err

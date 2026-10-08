"""Tests for haac_bridge/history and haac_bridge/statistics (concept 10.3, 11.2, 14.2)."""

from collections.abc import Callable, Coroutine
from datetime import timedelta
from typing import Any
from unittest.mock import patch

from homeassistant.auth.models import User
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util
import pytest
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)
from sqlalchemy.exc import OperationalError

CONFIG = {
    "users": [
        {
            "username": "anton",
            "filter": {
                "include_entities": ["sensor.living_room_temperature", "switch.garage_socket"]
            },
        }
    ]
}


@pytest.fixture
async def client(
    hass: HomeAssistant,
    add_user: Callable[[str], User],
    client_for: Callable[[User], Coroutine[Any, Any, Any]],
    setup_bridge: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
) -> Any:
    """Return a client for anton after recording a few state changes."""
    anton = add_user("anton")
    await setup_bridge(CONFIG)
    hass.states.async_set("sensor.living_room_temperature", "21.0", {"unit_of_measurement": "°C"})
    hass.states.async_set("sensor.bath_humidity", "55")
    hass.states.async_set("switch.garage_socket", "on")
    await async_wait_recording_done(hass)
    hass.states.async_set("sensor.living_room_temperature", "21.5", {"unit_of_measurement": "°C"})
    await async_wait_recording_done(hass)
    return await client_for(anton)


def _iso(delta: timedelta) -> str:
    """Return now + delta as ISO 8601 string."""
    return (dt_util.utcnow() + delta).isoformat()


async def _send(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    """Send a command and return its reply."""
    await client.send_json_auto_id(message)
    return await client.receive_json()


async def test_history_only_for_exposed_entities(client: Any) -> None:
    reply = await _send(
        client,
        {
            "type": "haac_bridge/history",
            "entity_ids": ["sensor.living_room_temperature", "sensor.bath_humidity"],
            "start": _iso(timedelta(hours=-1)),
        },
    )
    assert reply["success"], reply
    assert set(reply["result"]) == {"sensor.living_room_temperature"}
    assert [row["s"] for row in reply["result"]["sensor.living_room_temperature"]] == [
        "21.0",
        "21.5",
    ]


async def test_history_of_not_exposed_entities_is_empty(client: Any) -> None:
    reply = await _send(
        client,
        {
            "type": "haac_bridge/history",
            "entity_ids": ["sensor.bath_humidity"],
            "start": _iso(timedelta(hours=-1)),
        },
    )
    assert reply["result"] == {}


async def test_history_in_the_future_is_empty(client: Any) -> None:
    reply = await _send(
        client,
        {
            "type": "haac_bridge/history",
            "entity_ids": ["switch.garage_socket"],
            "start": _iso(timedelta(hours=1)),
        },
    )
    assert reply["result"] == {}


@pytest.mark.parametrize(
    "fields",
    [
        {"start": "yesterday"},
        {"start": "2026-09-28T10:00:00+00:00", "end": "2026-09-28T09:00:00+00:00"},
    ],
)
async def test_invalid_period_is_rejected(client: Any, fields: dict[str, str]) -> None:
    reply = await _send(
        client, {"type": "haac_bridge/history", "entity_ids": ["switch.garage_socket"], **fields}
    )
    assert reply["error"]["code"] == "HAB-WS-001"


async def test_recorder_error_is_reported(client: Any) -> None:
    with patch(
        "homeassistant.components.recorder.history.get_significant_states",
        side_effect=OperationalError("select", {}, Exception("db locked")),
    ):
        reply = await _send(
            client,
            {
                "type": "haac_bridge/history",
                "entity_ids": ["switch.garage_socket"],
                "start": _iso(timedelta(hours=-1)),
            },
        )
    assert reply["error"]["code"] == "HAB-HIST-001"


async def test_statistics_only_for_exposed_entities(hass: HomeAssistant, client: Any) -> None:
    start = dt_util.utcnow().replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)
    for statistic_id in ("sensor.living_room_temperature", "sensor.bath_humidity"):
        async_import_statistics(
            hass,
            {
                "mean_type": StatisticMeanType.ARITHMETIC,
                "has_sum": False,
                "name": None,
                "source": "recorder",
                "statistic_id": statistic_id,
                "unit_class": None,
                "unit_of_measurement": "°C",
            },
            [
                {"start": start + timedelta(hours=i), "mean": 21.0 + i, "min": 20.0, "max": 23.0}
                for i in range(2)
            ],
        )
    await async_wait_recording_done(hass)

    reply = await _send(
        client,
        {
            "type": "haac_bridge/statistics",
            "entity_ids": ["sensor.living_room_temperature", "sensor.bath_humidity"],
            "start": (start - timedelta(hours=1)).isoformat(),
            "period": "hour",
            "types": ["mean", "max"],
        },
    )
    assert reply["success"], reply
    assert set(reply["result"]) == {"sensor.living_room_temperature"}
    rows = reply["result"]["sensor.living_room_temperature"]
    assert [row["mean"] for row in rows] == [21.0, 22.0]
    assert rows[0]["start"] == int(start.timestamp() * 1000)


async def test_unknown_statistic_type_is_rejected(client: Any) -> None:
    reply = await _send(
        client,
        {
            "type": "haac_bridge/statistics",
            "entity_ids": ["sensor.living_room_temperature"],
            "start": _iso(timedelta(days=-1)),
            "types": ["last_reset"],
        },
    )
    assert reply["error"]["code"] == "HAB-WS-001"


async def test_at_most_50_entities_per_request(client: Any) -> None:
    entity_ids = [f"sensor.s{i}" for i in range(51)]
    reply = await _send(
        client,
        {
            "type": "haac_bridge/history",
            "entity_ids": entity_ids,
            "start": _iso(-timedelta(hours=1)),
        },
    )
    assert reply["error"]["code"] == "HAB-WS-001"

    reply = await _send(
        client,
        {
            "type": "haac_bridge/history",
            "entity_ids": entity_ids[:50],
            "start": _iso(-timedelta(hours=1)),
        },
    )
    assert reply["success"], reply


@pytest.mark.parametrize(
    ("command", "extra", "allowed", "too_long"),
    [
        ("haac_bridge/history", {}, timedelta(days=366), timedelta(days=367)),
        ("haac_bridge/statistics", {"period": "hour"}, timedelta(days=32), timedelta(days=33)),
        ("haac_bridge/statistics", {"period": "day"}, timedelta(days=1830), timedelta(days=1831)),
        ("haac_bridge/statistics", {"period": "month"}, timedelta(days=1830), timedelta(days=1831)),
    ],
)
async def test_the_period_is_limited(
    client: Any,
    command: str,
    extra: dict[str, str],
    allowed: timedelta,
    too_long: timedelta,
) -> None:
    end = dt_util.utcnow().replace(microsecond=0)
    base = {"type": command, "entity_ids": ["sensor.living_room_temperature"], **extra}

    reply = await _send(
        client, {**base, "start": (end - allowed).isoformat(), "end": end.isoformat()}
    )
    assert reply["success"], reply

    reply = await _send(
        client, {**base, "start": (end - too_long).isoformat(), "end": end.isoformat()}
    )
    assert reply["error"]["code"] == "HAB-HIST-002"


async def test_an_open_end_counts_up_to_now(client: Any) -> None:
    reply = await _send(
        client,
        {
            "type": "haac_bridge/history",
            "entity_ids": ["sensor.living_room_temperature"],
            "start": _iso(-timedelta(days=400)),
        },
    )
    assert reply["error"]["code"] == "HAB-HIST-002"

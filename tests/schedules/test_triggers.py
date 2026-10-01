"""Tests for the trigger planners and the TriggerFactory (concept 19.3, 18.2)."""

from datetime import date, datetime, timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_event_date
import pytest

from custom_components.haac_bridge.schedules.model import parse_when
from custom_components.haac_bridge.schedules.triggers import SunTrigger, TimeTrigger, TriggerFactory

from .conftest import ALL_DAYS, utc

SUN_FUNCTION = "custom_components.haac_bridge.schedules.triggers.get_astral_event_date"


def _event(hass: HomeAssistant, event: str, day: date, offset_min: int = 0) -> datetime:
    """Return the sun event of a day plus an offset, as the trigger should compute it."""
    moment = get_astral_event_date(hass, event, day)
    assert moment is not None
    return moment + timedelta(minutes=offset_min)


@pytest.mark.usefixtures("berlin")
async def test_factory_picks_the_planner_by_type(hass: HomeAssistant) -> None:
    factory = TriggerFactory(hass)
    assert isinstance(
        factory.create(parse_when({"type": "time", "time": "06:45", "days": ALL_DAYS})),
        TimeTrigger,
    )
    for kind in ("sunrise", "sunset"):
        assert isinstance(factory.create(parse_when({"type": kind, "days": ALL_DAYS})), SunTrigger)


@pytest.mark.usefixtures("berlin")
async def test_time_trigger_follows_the_ha_time_zone(hass: HomeAssistant) -> None:
    trigger = TriggerFactory(hass).create(
        parse_when({"type": "time", "time": "06:45", "days": ALL_DAYS})
    )
    assert trigger.next_run(utc(2026, 10, 5, 3, 0)) == utc(2026, 10, 5, 4, 45)
    assert trigger.previous_run(utc(2026, 10, 5, 12, 0)) == utc(2026, 10, 5, 4, 45)
    await hass.config.async_set_time_zone("Asia/Tokyo")
    tokyo = TriggerFactory(hass).create(
        parse_when({"type": "time", "time": "06:45", "days": ALL_DAYS})
    )
    assert tokyo.next_run(utc(2026, 10, 5, 3, 0)) == utc(2026, 10, 5, 21, 45)


@pytest.mark.usefixtures("berlin")
async def test_sunrise_with_offset(hass: HomeAssistant) -> None:
    trigger = TriggerFactory(hass).create(
        parse_when({"type": "sunrise", "days": ALL_DAYS, "offset_min": 30})
    )
    expected = _event(hass, "sunrise", date(2026, 10, 6), 30)
    assert trigger.next_run(utc(2026, 10, 5, 12, 0)) == expected
    assert trigger.previous_run(utc(2026, 10, 6, 12, 0)) == expected


@pytest.mark.usefixtures("berlin")
async def test_sunset_before_the_event(hass: HomeAssistant) -> None:
    trigger = TriggerFactory(hass).create(
        parse_when({"type": "sunset", "days": ALL_DAYS, "offset_min": -45})
    )
    assert trigger.next_run(utc(2026, 10, 5, 0, 0)) == _event(
        hass, "sunset", date(2026, 10, 5), -45
    )


@pytest.mark.usefixtures("berlin")
async def test_sun_trigger_filters_weekdays(hass: HomeAssistant) -> None:
    # 2026-10-05 is a Monday; Thursday (3) is 2026-10-08.
    trigger = TriggerFactory(hass).create(parse_when({"type": "sunrise", "days": [3]}))
    assert trigger.next_run(utc(2026, 10, 5, 12, 0)) == _event(hass, "sunrise", date(2026, 10, 8))
    assert trigger.previous_run(utc(2026, 10, 12, 12, 0)) == _event(
        hass, "sunrise", date(2026, 10, 8)
    )


@pytest.mark.usefixtures("berlin")
async def test_sun_trigger_without_events_gives_nothing(hass: HomeAssistant) -> None:
    trigger = TriggerFactory(hass).create(parse_when({"type": "sunrise", "days": ALL_DAYS}))
    with patch(SUN_FUNCTION, return_value=None):
        assert trigger.next_run(utc(2026, 10, 5, 12, 0)) is None
        assert trigger.previous_run(utc(2026, 10, 5, 12, 0)) is None

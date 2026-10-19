"""Tests for the trigger planners and the TriggerFactory (concept 19.3, 18.2)."""

from datetime import date, datetime, timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers.sun import get_astral_event_date
import pytest

from custom_components.haac_bridge.schedules.model import Repeat, parse_repeat, parse_when
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


def _repeat(freq: str, start: str, interval: int = 1, end: str | None = None) -> Repeat:
    """Return the repeat rule of a test with ISO dates."""
    return parse_repeat(
        {"freq": freq, "interval": None if freq == "once" else interval, "start_date": start}
        | ({"end_date": end} if end else {})
    )


@pytest.mark.usefixtures("berlin")
async def test_upcoming_lists_the_next_three_runs_of_the_rule(hass: HomeAssistant) -> None:
    when = parse_when({"type": "time", "time": "06:45"}, days_required=False)
    runs = TriggerFactory(hass).upcoming(
        when, _repeat("monthly", "2026-10-15"), utc(2026, 10, 1, 0, 0)
    )
    assert runs == [utc(2026, 10, 15, 4, 45), utc(2026, 11, 15, 5, 45), utc(2026, 12, 15, 5, 45)]


@pytest.mark.usefixtures("berlin")
async def test_upcoming_stops_at_the_end_date(hass: HomeAssistant) -> None:
    when = parse_when({"type": "time", "time": "06:45"}, days_required=False)
    repeat = _repeat("daily", "2026-10-05", end="2026-10-06")
    assert TriggerFactory(hass).upcoming(when, repeat, utc(2026, 10, 1, 0, 0)) == [
        utc(2026, 10, 5, 4, 45),
        utc(2026, 10, 6, 4, 45),
    ]
    assert TriggerFactory(hass).upcoming(when, repeat, utc(2026, 10, 6, 4, 45)) == []


@pytest.mark.usefixtures("berlin")
async def test_is_ended_when_the_rule_has_no_date_left(hass: HomeAssistant) -> None:
    factory = TriggerFactory(hass)
    when = parse_when({"type": "time", "time": "06:45"}, days_required=False)
    once = _repeat("once", "2026-10-05")
    assert not factory.is_ended(when, once, utc(2026, 10, 5, 3, 0))
    assert factory.is_ended(when, once, utc(2026, 10, 5, 4, 45))
    assert not factory.is_ended(when, _repeat("daily", "2026-10-05"), utc(2026, 12, 1, 0, 0))
    assert factory.is_ended(
        when, _repeat("daily", "2026-10-05", end="2026-10-31"), utc(2026, 11, 1, 0, 0)
    )


@pytest.mark.usefixtures("berlin")
async def test_sun_trigger_follows_a_monthly_rule(hass: HomeAssistant) -> None:
    when = parse_when({"type": "sunrise", "offset_min": 10}, days_required=False)
    runs = TriggerFactory(hass).upcoming(
        when, _repeat("monthly", "2026-10-15"), utc(2026, 10, 1, 0, 0)
    )
    assert runs == [
        _event(hass, "sunrise", date(2026, 10, 15), 10),
        _event(hass, "sunrise", date(2026, 11, 15), 10),
        _event(hass, "sunrise", date(2026, 12, 15), 10),
    ]


@pytest.mark.usefixtures("berlin")
async def test_sun_trigger_with_a_yearly_rule_looks_far_enough(hass: HomeAssistant) -> None:
    when = parse_when({"type": "sunset"}, days_required=False)
    trigger = TriggerFactory(hass).create(when, _repeat("yearly", "2026-03-01"))
    assert trigger.next_run(utc(2026, 3, 1, 23, 59)) == _event(hass, "sunset", date(2027, 3, 1))


@pytest.mark.usefixtures("berlin")
async def test_sun_trigger_once_is_ended_after_its_event_but_not_without_events(
    hass: HomeAssistant,
) -> None:
    factory = TriggerFactory(hass)
    when = parse_when({"type": "sunrise"}, days_required=False)
    once = _repeat("once", "2026-10-05")
    sunrise = _event(hass, "sunrise", date(2026, 10, 5))
    assert factory.create(when, once).next_run(sunrise - timedelta(hours=1)) == sunrise
    assert factory.is_ended(when, once, sunrise)
    daily = _repeat("daily", "2026-10-05")
    with patch(SUN_FUNCTION, return_value=None):
        assert factory.create(when, daily).next_run(utc(2026, 10, 5, 12, 0)) is None
        assert not factory.is_ended(when, daily, utc(2026, 10, 5, 12, 0))

"""Floors and areas that contain exposed entities (concept 6.3, 11.2)."""

from collections import Counter
from collections.abc import Iterable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
)


def _area_of(entity: er.RegistryEntry, devices: dr.DeviceRegistry) -> str | None:
    """Return the area of an entity: its own, else the area of its device."""
    if entity.area_id is not None:
        return entity.area_id
    if entity.device_id is None:
        return None
    device = devices.async_get(entity.device_id)
    return device.area_id if device else None


def _entity_counts(hass: HomeAssistant, entity_ids: Iterable[str]) -> Counter[str]:
    """Count the given entities per area ID; entities without an area are left out."""
    entities = er.async_get(hass)
    devices = dr.async_get(hass)
    counts: Counter[str] = Counter()
    for entity_id in entity_ids:
        entry = entities.async_get(entity_id)
        if entry is not None and (area_id := _area_of(entry, devices)) is not None:
            counts[area_id] += 1
    return counts


def area_catalog(hass: HomeAssistant, entity_ids: Iterable[str]) -> dict[str, Any]:
    """Return the areas that hold at least one of the entities, and the floors those areas are on.

    Areas are sorted by name; floors by level (floors without a level last), then name. Only names,
    levels and entity counts are returned, never entity IDs.
    """
    counts = _entity_counts(hass, entity_ids)
    areas = [
        {
            "area_id": area.id,
            "name": area.name,
            "floor_id": area.floor_id,
            "entity_count": counts[area.id],
        }
        for area in sorted(ar.async_get(hass).async_list_areas(), key=lambda a: a.name.casefold())
        if area.id in counts
    ]
    floor_ids = {area["floor_id"] for area in areas if area["floor_id"] is not None}
    floors = sorted(
        (
            {"floor_id": floor.floor_id, "name": floor.name, "level": floor.level}
            for floor in fr.async_get(hass).async_list_floors()
            if floor.floor_id in floor_ids
        ),
        key=lambda f: (f["level"] is None, f["level"] or 0, f["name"].casefold()),
    )
    return {"floors": floors, "areas": areas}

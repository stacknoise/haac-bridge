"""Attributes the bridge never passes to the app (review finding S5, concept 11.3).

The app shows all attributes of an entity (concept 8.1). Some attributes, however, name other
entities (the members of a group or the source of a min/max sensor) or carry a link with an
access token. Those are left out of descriptors, live events and history.
"""

from collections.abc import Mapping
from typing import Any

from homeassistant.core import CompressedState, State

HIDDEN_ATTRIBUTES = frozenset({"entity_id", "entities", "entity_picture", "access_token"})
"""Attribute names that are never sent; names ending in `_entity_id` are hidden as well."""


def is_hidden(name: str) -> bool:
    """Return True for an attribute that names other entities or carries an access link."""
    return name in HIDDEN_ATTRIBUTES or name.endswith("_entity_id")


def has_hidden(attributes: Mapping[str, Any]) -> bool:
    """Return True if any attribute must be left out; most states have none."""
    return any(is_hidden(name) for name in attributes)


def shareable_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Return the attributes without the hidden ones."""
    return {name: value for name, value in attributes.items() if not is_hidden(name)}


def shareable_state(state: State) -> State:
    """Return the state itself, or a copy without hidden attributes if it has any."""
    if not has_hidden(state.attributes):
        return state
    return State(
        state.entity_id,
        state.state,
        shareable_attributes(state.attributes),
        last_changed=state.last_changed,
        last_reported=state.last_reported,
        last_updated=state.last_updated,
        context=state.context,
        validate_entity_id=False,
    )


def compressed_state(state: State) -> CompressedState:
    """Return HA's compressed state for adds, without hidden attributes."""
    return shareable_state(state).as_compressed_state

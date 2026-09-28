"""Matches configured user entries to Home Assistant users (concept 10.2, 10.3)."""

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant

from .schema import UserEntry

_HA_AUTH_PROVIDER = "homeassistant"


def normalize_username(username: str) -> str:
    """Return the username in the form HA's own auth provider compares it."""
    return username.strip().casefold()


def usernames_of(user: User) -> set[str]:
    """Return the normalized login names of a user from its HA auth provider credentials."""
    return {
        normalize_username(credential.data["username"])
        for credential in user.credentials
        if credential.auth_provider_type == _HA_AUTH_PROVIDER and "username" in credential.data
    }


def entry_matches(entry: UserEntry, user: User) -> bool:
    """Return True if the configuration entry refers to this HA user."""
    if entry.user_id is not None:
        return entry.user_id == user.id
    if entry.username is not None:
        return normalize_username(entry.username) in usernames_of(user)
    return False


async def async_find_unknown_entries(
    hass: HomeAssistant, entries: list[UserEntry]
) -> list[UserEntry]:
    """Return the entries that match no existing HA user."""
    users = await hass.auth.async_get_users()
    return [entry for entry in entries if not any(entry_matches(entry, user) for user in users)]

"""Per-user set of exposed entities and its revision hash (concept 10.2, 10.3)."""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant, split_entity_id

from ..config.schema import UserEntry
from ..config.users import entry_matches
from ..const import SUPPORTED_DOMAINS
from .filter_factory import EntityPredicate, FilterFactory


@dataclass(frozen=True, slots=True)
class ExposureSnapshot:
    """The entities exposed to one user at one moment, their configured names and revision."""

    entity_ids: list[str]
    names: dict[str, str]
    revision: str


@dataclass(frozen=True, slots=True)
class _UserRule:
    """A configured user entry together with its built filter."""

    entry: UserEntry
    predicate: EntityPredicate


class Exposure:
    """Decides which entities a HA user sees; deny by default for users not configured."""

    def __init__(self, entries: list[UserEntry], filters: FilterFactory) -> None:
        """Build one filter per configured user entry."""
        self._rules = [_UserRule(entry, filters.create(entry)) for entry in entries]

    def is_exposed(self, user: User, entity_id: str) -> bool:
        """Return True if the entity is in a v1 domain and passes the user's filter."""
        rule = self._rule_for(user)
        if rule is None:
            return False
        domain = split_entity_id(entity_id)[0]
        return domain in SUPPORTED_DOMAINS and rule.predicate(entity_id)

    def filter_exposed(self, user: User, entity_ids: list[str]) -> list[str]:
        """Return the requested IDs the user may see, sorted and without duplicates."""
        return sorted({entity_id for entity_id in entity_ids if self.is_exposed(user, entity_id)})

    def exposed_entity_ids(self, hass: HomeAssistant, user: User) -> list[str]:
        """Return the sorted IDs of all current entities exposed to the user."""
        rule = self._rule_for(user)
        if rule is None:
            return []
        return sorted(
            state.entity_id
            for state in hass.states.async_all(SUPPORTED_DOMAINS)
            if rule.predicate(state.entity_id)
        )

    def configured_names(self, user: User) -> dict[str, str]:
        """Return the names from `entity_config` that apply to the user (global, then own)."""
        rule = self._rule_for(user)
        return dict(rule.entry.names) if rule else {}

    def snapshot(self, hass: HomeAssistant, user: User) -> ExposureSnapshot:
        """Return the user's exposed entities with their configured names and revision."""
        entity_ids = self.exposed_entity_ids(hass, user)
        names = self.configured_names(user)
        exposed = {entity_id: names[entity_id] for entity_id in entity_ids if entity_id in names}
        return ExposureSnapshot(entity_ids, exposed, compute_revision(entity_ids, names))

    def _rule_for(self, user: User) -> _UserRule | None:
        """Return the first rule whose entry refers to the user."""
        return next((rule for rule in self._rules if entry_matches(rule.entry, user)), None)


def compute_revision(entity_ids: list[str], names: Mapping[str, str] | None = None) -> str:
    """Return a stable hash of an exposed set and its configured names.

    It changes when entities are added or removed or a configured name changes; without
    names it equals the hash of the bare set.
    """
    names = names or {}
    digest = hashlib.sha256()
    for entity_id in sorted(entity_ids):
        digest.update(entity_id.encode())
        if (name := names.get(entity_id)) is not None:
            digest.update(b"\t" + name.encode())
        digest.update(b"\n")
    return digest.hexdigest()

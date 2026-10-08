"""Per-user set of exposed entities and its revision hash (concept 10.2, 10.3)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib

from homeassistant.auth.models import User
from homeassistant.core import HomeAssistant, callback, split_entity_id

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


CACHE_LIMIT = 10_000
"""Most cached (user, entity) answers; the cache starts over when it is full."""


def _nothing_excluded(entity_id: str) -> bool:
    """Exclude no entity; the default when the caller has no entities of its own to hide."""
    return False


class Exposure:
    """Decides which entities a HA user sees; deny by default for users not configured."""

    def __init__(
        self,
        entries: list[UserEntry],
        filters: FilterFactory,
        is_own_entity: Callable[[str], bool] = _nothing_excluded,
    ) -> None:
        """Build one filter per configured user entry; `is_own_entity` marks entities never exposed.

        Answers are cached (review finding P1, P3): the rule per user, the decision per user and
        entity, and the exposed set per user. The `async_invalidate_*` methods clear them.
        """
        self._rules = [_UserRule(entry, filters.create(entry)) for entry in entries]
        self._is_own_entity = is_own_entity
        self._rule_by_user: dict[str, _UserRule | None] = {}
        self._decisions: dict[tuple[str, str], bool] = {}
        self._exposed_sets: dict[str, list[str]] = {}

    @callback
    def async_invalidate_users(self) -> None:
        """Forget everything; a HA user was added, changed or removed (login names can change)."""
        self._rule_by_user.clear()
        self.async_invalidate_registry()

    @callback
    def async_invalidate_registry(self) -> None:
        """Forget decisions and sets; the entity registry changed (own entities, renamed IDs)."""
        self._decisions.clear()
        self._exposed_sets.clear()

    @callback
    def async_invalidate_states(self) -> None:
        """Forget the exposed sets; an entity appeared in or left the state machine."""
        self._exposed_sets.clear()

    def is_configured(self, user: User) -> bool:
        """Return True if the user has an entry in the YAML or the UI configuration."""
        return self._rule_for(user) is not None

    def is_exposed(self, user: User, entity_id: str) -> bool:
        """Return True if the entity is in a v1 domain, passes the user's filter and is not the bridge's own.

        The domain is checked first: it is the cheapest test and rejects most state changes.
        """
        if split_entity_id(entity_id)[0] not in SUPPORTED_DOMAINS:
            return False
        key = (user.id, entity_id)
        if (decision := self._decisions.get(key)) is not None:
            return decision
        rule = self._rule_for(user)
        decision = (
            rule is not None and rule.predicate(entity_id) and not self._is_own_entity(entity_id)
        )
        if len(self._decisions) >= CACHE_LIMIT:
            self._decisions.clear()
        self._decisions[key] = decision
        return decision

    def filter_exposed(self, user: User, entity_ids: list[str]) -> list[str]:
        """Return the requested IDs the user may see, sorted and without duplicates."""
        return sorted({entity_id for entity_id in entity_ids if self.is_exposed(user, entity_id)})

    def exposed_entity_ids(self, hass: HomeAssistant, user: User) -> list[str]:
        """Return the sorted IDs of all current entities exposed to the user."""
        rule = self._rule_for(user)
        if rule is None:
            return []
        if (cached := self._exposed_sets.get(user.id)) is None:
            cached = sorted(
                state.entity_id
                for state in hass.states.async_all(SUPPORTED_DOMAINS)
                if rule.predicate(state.entity_id) and not self._is_own_entity(state.entity_id)
            )
            self._exposed_sets[user.id] = cached
        return list(cached)

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
        """Return the first rule whose entry refers to the user, looked up once per user."""
        try:
            return self._rule_by_user[user.id]
        except KeyError:
            rule = next((rule for rule in self._rules if entry_matches(rule.entry, user)), None)
            self._rule_by_user[user.id] = rule
            return rule


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

"""Skipped runs: a date rule that leaves out chosen dates (concept 19.12).

Like `recurrence.py` this module needs only the standard library besides the rule it wraps.
"""

from __future__ import annotations

from datetime import date, timedelta

from .recurrence import DateRule

DAY = timedelta(days=1)


class SkippingRule:
    """A date rule without the dates the user skipped; every other date is the inner rule's."""

    def __init__(self, inner: DateRule, skipped: frozenset[date]) -> None:
        """Wrap the rule and remember the skipped dates (a few, at most `MAX_SKIPPED_DATES`)."""
        self._inner = inner
        self._skipped = skipped

    def matches(self, day: date) -> bool:
        """Return whether the schedule runs on `day`: the rule says so and the date is not skipped."""
        return day not in self._skipped and self._inner.matches(day)

    def next_date(self, after: date) -> date | None:
        """Return the first run date strictly after `after` that is not skipped, or None."""
        found = self._inner.next_date(after)
        while found is not None and found in self._skipped:
            found = self._inner.next_date(found)
        return found

    def previous_date(self, before: date) -> date | None:
        """Return the last run date on or before `before` that is not skipped, or None."""
        found = self._inner.previous_date(before)
        while found is not None and found in self._skipped:
            found = self._inner.previous_date(found - DAY)
        return found

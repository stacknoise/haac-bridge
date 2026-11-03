"""Formatting of values for log lines (concept 21.7)."""

import json
import re
from typing import Any

_PLAIN = re.compile(r"^[A-Za-z0-9_.:/@-]+$")
_LINE_BREAKS = str.maketrans({"\u2028": "\\u2028", "\u2029": "\\u2029", "\x85": "\\u0085"})


def format_value(value: Any) -> str:
    """Return a value for a log line: plain words as they are, everything else as JSON.

    JSON escapes line breaks and quotes, so text typed by a user cannot forge a second log line (concept 21.7).
    """
    if value is None:
        return "none"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str) and _PLAIN.match(value):
        return value
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return text.translate(_LINE_BREAKS)

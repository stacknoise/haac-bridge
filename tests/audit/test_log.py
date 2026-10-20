"""Tests for the log line format (concept 21.3, 21.7)."""

import logging

import pytest

from custom_components.haac_bridge.audit.entry import AuditEntry
from custom_components.haac_bridge.audit.log import format_line, format_value

LS = chr(0x2028)
PS = chr(0x2029)


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (None, "none"),
        (True, "true"),
        (21.5, "21.5"),
        ("switch.garage_socket", "switch.garage_socket"),
        ("Pixel 8", '"Pixel 8"'),
        ({"temperature": 21.5}, '{"temperature": 21.5}'),
    ],
)
def test_format_value(value: object, text: str) -> None:
    assert format_value(value) == text


@pytest.mark.parametrize("name", ["a\nb", "a\rb", f"a{LS}b", f"a{PS}b", "a\x85b"])
def test_a_device_name_cannot_start_a_second_line(name: str) -> None:
    line = format_line(AuditEntry("call_service", logging.INFO, (("client", name),)))
    assert len(line.splitlines()) == 1
    assert LS not in line
    assert PS not in line
    assert "\x85" not in line


def test_a_line_is_the_action_and_its_fields() -> None:
    entry = AuditEntry("call_service", logging.INFO, (("source", "app"), ("ms", 12)))
    assert format_line(entry) == "action=call_service source=app ms=12"

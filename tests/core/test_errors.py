"""Tests for error codes, exceptions and the ErrorFactory (concept 18.3)."""

import json
from pathlib import Path
import re

import pytest
import voluptuous as vol

from custom_components.haac_bridge.core import errors
from custom_components.haac_bridge.core.error_factory import ErrorFactory
from custom_components.haac_bridge.core.errors import (
    APP_CODES,
    ErrorCode,
    HaacBridgeError,
    InternalError,
    RequestError,
)

TRANSLATIONS = (
    Path(__file__).parents[2] / "custom_components" / "haac_bridge" / "translations" / "en.json"
)
CODE_FORMAT = re.compile(r"^HAB-(CFG|AUTH|SVC|ENT|HIST|WS|INT)-\d{3}$")


async def test_codes_are_unique_and_well_formed() -> None:
    values = [code.value for code in ErrorCode]
    assert len(values) == len(set(values))
    for value in values:
        assert CODE_FORMAT.match(value), value


async def test_every_code_has_translation_and_app_mapping() -> None:
    messages = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))["exceptions"]
    for code in ErrorCode:
        assert messages[code.translation_key]["message"], code
        assert code in APP_CODES, code


@pytest.mark.parametrize(
    ("cls", "area"),
    [
        (errors.ConfigError, "CFG"),
        (errors.NotAllowedError, "AUTH"),
        (errors.InvalidServiceError, "SVC"),
        (errors.EntityNotFoundError, "ENT"),
        (errors.HistoryError, "HIST"),
        (errors.RequestError, "WS"),
        (errors.InternalError, "INT"),
    ],
)
async def test_subclass_default_code_matches_area(cls: type[HaacBridgeError], area: str) -> None:
    error = cls()
    assert error.code.area == area
    assert error.translation_domain == "haac_bridge"
    assert error.translation_key == error.code.translation_key


async def test_error_factory_mapping() -> None:
    factory = ErrorFactory()
    own = RequestError()
    assert factory.from_exception(own) is own
    assert isinstance(factory.from_exception(vol.Invalid("bad")), RequestError)
    assert isinstance(factory.from_exception(KeyError("x")), InternalError)

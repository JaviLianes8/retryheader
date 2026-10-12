"""The serialiser against the httpwg suite: canonical forms and serialisation-tests.

The suite is fetched locally (tests/upstream/MANIFEST.json); these tests skip until then.
"""

from __future__ import annotations

import base64
from typing import Any

import pytest

from retryheader._sf import parse_item, parse_list
from retryheader._sf_serialize import serialize_bare, serialize_list, serialize_params
from retryheader._sf_types import BareItem, Date, DisplayString, Token
from tests.upstream_files import SKIP_REASON, fetched, json_files


def _load(prefix: str) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for stem, cases in json_files(prefix):
        for case in cases:
            if case["header_type"] in ("list", "item"):
                out.append((f"{stem}: {case['name']}", case))
    return out


def _has_inner_list(case: dict[str, Any]) -> bool:
    return case["header_type"] == "list" and any(
        isinstance(member[0], list) for member in case["expected"]
    )


CANONICAL = [
    pytest.param(case, id=name)
    for name, case in _load("")
    if not case.get("must_fail") and not _has_inner_list(case)
]
SERIALISATION = [pytest.param(case, id=name) for name, case in _load("serialisation-tests")]


@pytest.mark.skipif(not fetched(), reason=SKIP_REASON)
def test_the_cases_are_loaded() -> None:
    assert len(CANONICAL) == 579
    assert len(SERIALISATION) == 355


@pytest.mark.parametrize("case", CANONICAL)
def test_parse_then_serialise_gives_the_canonical_form(case: dict[str, Any]) -> None:
    text = ", ".join(case["raw"])
    # The suite's README: the canonical form is `canonical` if given, otherwise `raw`.
    expected = ", ".join(case.get("canonical", case["raw"]))
    if case["header_type"] == "item":
        value, params = parse_item(text)
        assert serialize_bare(value) + serialize_params(params) == expected
    else:
        members: Any = parse_list(text)
        assert serialize_list(members) == expected


@pytest.mark.parametrize("case", SERIALISATION)
def test_serialisation_case(case: dict[str, Any]) -> None:
    if case["header_type"] == "item":
        members = [_item(case["expected"])]
    else:
        members = [_item(member) for member in case["expected"]]
    if case.get("must_fail"):
        with pytest.raises((ValueError, TypeError)):
            serialize_list(members)
        return
    assert serialize_list(members) == ", ".join(case["canonical"])


def _item(raw: list[Any]) -> tuple[BareItem, dict[str, BareItem]]:
    return _bare(raw[0]), {key: _bare(value) for key, value in raw[1]}


def _bare(raw: Any) -> BareItem:
    if isinstance(raw, dict):
        kind, value = raw["__type"], raw["value"]
        if kind == "token":
            return Token(value)
        if kind == "binary":
            return base64.b32decode(value)
        if kind == "date":
            return Date(value)
        return DisplayString(value)
    plain: BareItem = raw
    return plain

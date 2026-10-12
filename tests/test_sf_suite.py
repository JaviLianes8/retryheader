"""The structured field parser against the httpwg test suite.

The suite is not committed: tests/upstream/MANIFEST.json pins its files and
`python scripts/fetch_upstream.py` fetches them. These tests skip until then.
"""

from __future__ import annotations

import base64
from typing import Any

import pytest

from retryheader._sf import Member, parse_item, parse_list
from retryheader._sf_scalars import SFError
from retryheader._sf_types import BareItem, Date, DisplayString, Token
from tests.upstream_files import SKIP_REASON, fetched, json_files


def _cases() -> list[Any]:
    cases = []
    for stem, file_cases in json_files():
        for case in file_cases:
            if case["header_type"] in ("list", "item"):
                cases.append(pytest.param(case, id=f"{stem}: {case['name']}"))
    return cases


CASES = _cases()


@pytest.mark.skipif(not fetched(), reason=SKIP_REASON)
def test_the_suite_is_loaded() -> None:
    # Guards against a glob or filter change that silently skips the suite.
    assert len(CASES) == 1157


@pytest.mark.parametrize("case", CASES)
def test_suite_case(case: dict[str, Any]) -> None:
    check_case(case)


def check_case(case: dict[str, Any]) -> None:
    """Parse one suite case and compare it with its expected value or failure."""
    text = ", ".join(case["raw"])
    parse = parse_list if case["header_type"] == "list" else parse_item
    if case.get("must_fail"):
        with pytest.raises(SFError):
            parse(text)
        return
    try:
        parsed: Any = parse(text)
    except SFError:
        assert case.get("can_fail"), f"rejected a valid field: {text!r}"
        return
    actual = [_member(m) for m in parsed] if case["header_type"] == "list" else _item(parsed)
    assert _typed(actual) == _typed(case["expected"])


def _typed(value: Any) -> Any:
    # Tag scalars with their type: 1, 1.0 and True compare equal in Python, but an
    # Integer, a Decimal and a Boolean are different structured field values.
    if isinstance(value, list):
        return [_typed(v) for v in value]
    if isinstance(value, dict):
        return {k: _typed(v) for k, v in value.items()}
    return (type(value).__name__, value)


def _member(member: Member) -> Any:
    value, params = member
    if isinstance(value, list):
        return [[_item(item) for item in value], _params(params)]
    return _item((value, params))


def _item(item: tuple[BareItem, dict[str, BareItem]]) -> Any:
    return [_bare(item[0]), _params(item[1])]


def _params(params: dict[str, BareItem]) -> Any:
    return [[key, _bare(value)] for key, value in params.items()]


def _bare(value: BareItem) -> Any:
    if isinstance(value, Token):
        return {"__type": "token", "value": str(value)}
    if isinstance(value, DisplayString):
        return {"__type": "displaystring", "value": str(value)}
    if isinstance(value, Date):
        return {"__type": "date", "value": value.seconds}
    if isinstance(value, bytes):
        return {"__type": "binary", "value": base64.b32encode(value).decode("ascii")}
    return value

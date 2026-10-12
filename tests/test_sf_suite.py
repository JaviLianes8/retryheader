"""The structured field parser against the httpwg test suite (see fixtures/sf/SOURCE.txt)."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest

from retryheader._sf import Member, parse_item, parse_list
from retryheader._sf_scalars import SFError
from retryheader._sf_types import BareItem, Date, DisplayString, Token

FIXTURES = Path(__file__).parent / "fixtures" / "sf"


def _cases() -> list[Any]:
    cases = []
    for path in sorted(FIXTURES.glob("*.json")):
        for case in json.loads(path.read_text(encoding="utf-8")):
            if case["header_type"] in ("list", "item"):
                cases.append(pytest.param(case, id=f"{path.stem}: {case['name']}"))
    return cases


CASES = _cases()


def test_the_suite_is_loaded() -> None:
    # Guards against a glob or filter change that silently skips the suite.
    assert len(CASES) == 1157


@pytest.mark.parametrize("case", CASES)
def test_suite_case(case: dict[str, Any]) -> None:
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
    if case["header_type"] == "list":
        assert [_member(m) for m in parsed] == case["expected"]
    else:
        assert _item(parsed) == case["expected"]


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

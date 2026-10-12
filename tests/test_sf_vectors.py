"""Short structured field vectors cited from the httpwg test suite; always run.

Each case is copied unchanged from one file of the suite at commit
781ba38464b2ec4c547e1e14d007d4f5ace7457e, fetched 2026-10-13; the file is
https://raw.githubusercontent.com/httpwg/structured-field-tests/<commit>/<file> (BSD-3-Clause,
IETF Trust). The full suite runs from tests/upstream when fetched.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.test_sf_suite import check_case

BASE = "https://raw.githubusercontent.com/httpwg/structured-field-tests/781ba38464b2ec4c547e1e14d007d4f5ace7457e/"

VECTORS: list[tuple[str, dict[str, Any]]] = [
    (
        BASE + "list.json",
        {
            "name": "basic list",
            "raw": ["1, 42"],
            "header_type": "list",
            "expected": [[1, []], [42, []]],
        },
    ),
    (
        BASE + "list.json",
        {
            "name": "no whitespace list",
            "raw": ["1,42"],
            "header_type": "list",
            "expected": [[1, []], [42, []]],
            "canonical": ["1, 42"],
        },
    ),
    (
        BASE + "item.json",
        {"name": "empty item", "raw": [""], "header_type": "item", "must_fail": True},
    ),
    (
        BASE + "item.json",
        {
            "name": "leading and trailing space",
            "raw": ["  1  "],
            "header_type": "item",
            "expected": [1, []],
            "canonical": ["1"],
        },
    ),
    (
        BASE + "number.json",
        {
            "name": "negative zero",
            "raw": ["-0"],
            "header_type": "item",
            "expected": [0, []],
            "canonical": ["0"],
        },
    ),
    (
        BASE + "number.json",
        {"name": "double negative zero", "raw": ["--0"], "header_type": "item", "must_fail": True},
    ),
    (
        BASE + "string.json",
        {
            "name": "basic string",
            "raw": ['"foo bar"'],
            "header_type": "item",
            "expected": ["foo bar", []],
        },
    ),
    (
        BASE + "string.json",
        {"name": "non-ascii string", "raw": ['"füü"'], "header_type": "item", "must_fail": True},
    ),
    (
        BASE + "token.json",
        {
            "name": "basic token - item",
            "raw": ["a_b-c.d3:f%00/*"],
            "header_type": "item",
            "expected": [{"__type": "token", "value": "a_b-c.d3:f%00/*"}, []],
        },
    ),
    (
        BASE + "binary.json",
        {
            "name": "basic binary",
            "raw": [":aGVsbG8=:"],
            "header_type": "item",
            "expected": [{"__type": "binary", "value": "NBSWY3DP"}, []],
        },
    ),
    (
        BASE + "binary.json",
        {
            "name": "padding in middle",
            "raw": [":a=GVsbG8=:"],
            "header_type": "item",
            "must_fail": True,
        },
    ),
    (
        BASE + "boolean.json",
        {
            "name": "basic true boolean",
            "raw": ["?1"],
            "header_type": "item",
            "expected": [True, []],
        },
    ),
    (
        BASE + "boolean.json",
        {"name": "unknown boolean", "raw": ["?Q"], "header_type": "item", "must_fail": True},
    ),
    (
        BASE + "date.json",
        {
            "name": "date - 2022-08-04 01:57:13",
            "raw": ["@1659578233"],
            "header_type": "item",
            "expected": [{"__type": "date", "value": 1659578233}, []],
        },
    ),
    (
        BASE + "display-string.json",
        {
            "name": "non-ascii display string (lowercase escaping)",
            "raw": ['%"f%c3%bc%c3%bc"'],
            "header_type": "item",
            "expected": [{"__type": "displaystring", "value": "füü"}, []],
        },
    ),
    (
        BASE + "display-string.json",
        {
            "name": "non-ascii display string (uppercase escaping)",
            "raw": ['%"f%C3%BC%C3%BC"'],
            "header_type": "item",
            "must_fail": True,
        },
    ),
    (
        BASE + "param-list.json",
        {
            "name": "single item parameterised list",
            "raw": ["text/html;q=1.0"],
            "header_type": "list",
            "expected": [[{"__type": "token", "value": "text/html"}, [["q", 1.0]]]],
        },
    ),
    (
        BASE + "param-list.json",
        {
            "name": "whitespace before = parameterised list",
            "raw": ["text/html, text/plain;q =0.5"],
            "header_type": "list",
            "must_fail": True,
        },
    ),
    (
        BASE + "listlist.json",
        {
            "name": "basic list of lists",
            "raw": ["(1 2), (42 43)"],
            "header_type": "list",
            "expected": [[[[1, []], [2, []]], []], [[[42, []], [43, []]], []]],
        },
    ),
    (
        BASE + "listlist.json",
        {
            "name": "wrong whitespace list of lists",
            "raw": ["(1\t 42)"],
            "header_type": "list",
            "must_fail": True,
        },
    ),
]


@pytest.mark.parametrize(("url", "case"), VECTORS, ids=[c["name"] for _, c in VECTORS])
def test_cited_vector(url: str, case: dict[str, Any]) -> None:
    assert url.startswith(BASE)
    check_case(case)

"""Contracts on extra values: typed equality, read-only storage, decimal rounding, messages."""

from __future__ import annotations

import copy
import pickle
from typing import Any

import pytest

from retryheader import (
    QuotaPolicy,
    ServiceLimit,
    build_ratelimit,
    build_ratelimit_policy,
    delay_from_headers,
    parse_ratelimit,
)

# Pairs of fields whose only difference is the structured-field type of one parameter.
TYPED_PAIRS = [
    ('"a";r=1;k', '"a";r=1;k=1'),
    ('"a";r=1;k=1', '"a";r=1;k=1.0'),
    ('"a";r=1;k=x', '"a";r=1;k="x"'),
    ('"a";r=1;k=%"x"', '"a";r=1;k="x"'),
    ('"a";r=1;k=%"x"', '"a";r=1;k=x'),
    ('"a";r=1;k=?0', '"a";r=1;k=0'),
]


@pytest.mark.parametrize(("first", "second"), TYPED_PAIRS)
def test_limits_differing_in_an_extra_type_are_not_equal(first: str, second: str) -> None:
    (a,), (b,) = parse_ratelimit(first), parse_ratelimit(second)
    assert build_ratelimit([a]) != build_ratelimit([b])
    assert a != b and (a == b) is False
    assert a.extra != b.extra and (a.extra == b.extra) is False
    assert len({a, b}) == 2


@pytest.mark.parametrize(("first", "second"), TYPED_PAIRS)
def test_extra_hash_follows_the_type(first: str, second: str) -> None:
    (a,), (b,) = parse_ratelimit(first), parse_ratelimit(second)
    assert hash(a.extra) != hash(b.extra)


def test_limits_with_the_same_typed_extra_are_equal() -> None:
    field = '"a";r=1;k;n=1;f=1.0;tk=x;s="x";d=%"x";b=:eA==:;at=@0'
    (a,), (b,) = parse_ratelimit(field), parse_ratelimit(field)
    assert a == b and hash(a) == hash(b) and hash(a.extra) == hash(b.extra)
    assert len({a, b}) == 1
    assert pickle.loads(pickle.dumps(a)) == a and copy.deepcopy(a) == a


def test_extra_still_compares_with_a_plain_dict_by_value() -> None:
    (limit,) = parse_ratelimit('"a";r=1;k=x;n=1')
    assert limit.extra == {"k": "x", "n": 1}
    assert QuotaPolicy("p", 1, extra={"k": 1}) != QuotaPolicy("p", 1, extra={"k": True})


@pytest.mark.parametrize("make", [ServiceLimit, QuotaPolicy])
def test_extra_cannot_be_reinitialised(make: Any) -> None:
    item = make("a", 1, extra={"k": 1})
    seen = {item}
    with pytest.raises(TypeError, match="extra parameters are read only"):
        item.extra.__init__({"k": 2, "evil": "x"})
    assert dict(item.extra) == {"k": 1} and item in seen


def test_a_fresh_extra_mapping_still_builds() -> None:
    limit = ServiceLimit("a", 1, extra={"k": 1})
    fresh: Any = type(limit.extra)
    assert fresh({"x": 2}) == {"x": 2}
    assert build_ratelimit([limit]) == '"a";r=1;k=1'


@pytest.mark.parametrize(
    ("value", "wire"),
    [
        # A float rounds as the shortest decimal that reads back as it (its repr), the
        # number the caller wrote, so the httpwg serialisation vectors hold.
        (0.0025, "0.002"),
        (-0.0025, "-0.002"),
        (0.0015, "0.002"),
        (9.9995, "10.0"),
        (0.1235, "0.124"),
        (0.0005, "0.0"),
        (-649356.5595, "-649356.56"),
        (0.12351, "0.124"),
    ],
)
def test_a_float_rounds_as_its_repr_half_to_even(value: float, wire: str) -> None:
    assert build_ratelimit([ServiceLimit("a", 1, extra={"x": value})]) == f'"a";r=1;x={wire}'
    policy = QuotaPolicy("a", 1, extra={"x": value})
    assert build_ratelimit_policy([policy]) == f'"a";q=1;x={wire}'


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (
            lambda: delay_from_headers({"X-Other": 5}),  # type: ignore[arg-type]
            "header names and values must be str",
        ),
        (
            lambda: delay_from_headers([(5, "1")]),  # type: ignore[list-item]
            "header names and values must be str",
        ),
        (
            lambda: ServiceLimit("a", 1, extra={1: "x"}),  # type: ignore[dict-item]
            "extra parameter names must be str, not int",
        ),
        (
            lambda: QuotaPolicy("a", 1, extra={b"k": "x"}),  # type: ignore[dict-item]
            "extra parameter names must be str, not bytes",
        ),
        (
            lambda: ServiceLimit("a", 1, partition_key="x"),  # type: ignore[arg-type]
            "partition_key must be bytes or None, not str",
        ),
        (
            lambda: QuotaPolicy("a", 1, partition_key=bytearray(b"x")),  # type: ignore[arg-type]
            "partition_key must be bytes or None, not bytearray",
        ),
    ],
)
def test_type_guards_say_what_is_wrong(call: Any, message: str) -> None:
    with pytest.raises(TypeError, match=f"^{message}$"):
        call()

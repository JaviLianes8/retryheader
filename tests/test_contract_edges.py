"""Contracts for the edges fixed in 1.0.0: each failed on 0.2.1."""

from __future__ import annotations

import dataclasses
import decimal
import pickle
from datetime import datetime, timezone

import pytest

from retryheader import (
    QuotaPolicy,
    RateLimitError,
    RetryAfterError,
    ServiceLimit,
    build_ratelimit,
    parse_http_date,
    parse_ratelimit,
    parse_retry_after,
)

# Written by retryheader 0.2.1 from PyPI (pickle protocol 4) on CPython 3.13, 2026-10-18.
OLD_LIMIT = bytes.fromhex(
    "800495aa000000000000008c1c72657472796865616465722e5f726174656c696d69745f7479706573948c0c"
    "536572766963654c696d69749493942981947d94288c06706f6c696379948c056275727374948c0972656d61"
    "696e696e67944b008c0677696e646f77944b1e8c0d706172746974696f6e5f6b6579944306757365722d3194"
    "8c0565787472619468008c0d5f526561644f6e6c79446963749493947d948c0461636d65948c017894738594"
    "529475622e"
)
OLD_POLICY = bytes.fromhex(
    "80049501010000000000008c1c72657472796865616465722e5f726174656c696d69745f7479706573948c0b"
    "51756f7461506f6c6963799493942981947d94288c046e616d65948c056461696c79948c0571756f7461944d"
    "e8038c0677696e646f77944a805101008c04756e6974948c087265717565737473948c0d706172746974696f"
    "6e5f6b6579944e8c0565787472619468008c0d5f526561644f6e6c79446963749493947d948c026174948c08"
    "6461746574696d65948c086461746574696d65949394430a07ea01010000000000009468118c0874696d657a"
    "6f6e6594939468118c0974696d6564656c74619493944b004b004b00879452948594529486945294738594"
    "529475622e"
)


def test_pickles_written_by_0_2_1_still_load() -> None:
    limit = pickle.loads(OLD_LIMIT)
    assert limit == ServiceLimit("burst", 0, 30, b"user-1", {"acme": "x"})
    policy = pickle.loads(OLD_POLICY)
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert policy == QuotaPolicy("daily", 1000, 86400, extra={"at": at})
    with pytest.raises(TypeError):
        policy.extra["at"] = at


def test_no_field_default_is_a_dict() -> None:
    # Python 3.10 refuses a dict (or dict subclass) as a dataclass default at import.
    for cls in (QuotaPolicy, ServiceLimit):
        for field in dataclasses.fields(cls):
            assert not isinstance(field.default, dict), field.name


def test_each_instance_gets_its_own_read_only_extra() -> None:
    first, second = ServiceLimit("a", 1), ServiceLimit("b", 1)
    assert dict(first.extra) == {} and first.extra is not second.extra
    with pytest.raises(TypeError):
        first.extra.clear()  # type: ignore[attr-defined]


def test_the_callers_decimal_context_changes_nothing() -> None:
    limit = ServiceLimit("a", 1, extra={"x": 12345.678, "y": 0.0025, "z": -0.0005})
    expected = '"a";r=1;x=12345.678;y=0.002;z=0.0'  # -0.000 is not below zero
    with decimal.localcontext() as context:
        context.prec = 3
        context.traps[decimal.Inexact] = context.traps[decimal.Rounded] = True
        assert build_ratelimit([limit]) == expected
    assert build_ratelimit([limit]) == expected


@pytest.mark.parametrize("value", [1e13, 1e26, 1e300, -1e300, float("inf")])
def test_a_float_too_large_for_a_decimal_is_a_value_error(value: float) -> None:
    with pytest.raises(ValueError, match="out of structured field range"):
        build_ratelimit([ServiceLimit("a", 1, extra={"x": value})])


class _Sneaky(str):
    """A str subclass whose own methods lie; the library must read the characters."""

    def strip(self, chars: str | None = None) -> str:
        return "120"

    def isdigit(self) -> bool:
        return True

    def __repr__(self) -> str:
        raise RuntimeError("no repr")


def test_str_subclasses_are_read_as_their_characters() -> None:
    with pytest.raises(RetryAfterError, match="'soon'"):
        parse_retry_after(_Sneaky("soon"))
    assert parse_retry_after(_Sneaky(" 7 ")) == 7.0
    with pytest.raises(RetryAfterError):
        parse_http_date(_Sneaky("yesterday"))
    assert parse_ratelimit(_Sneaky('"a";r=1'))[0].remaining == 1
    with pytest.raises(RateLimitError):
        parse_ratelimit([_Sneaky('"a";r=-1')])


def test_a_huge_integer_is_described_by_its_size() -> None:
    with pytest.raises(ValueError, match="an integer of 16610 bits") as caught:
        QuotaPolicy("a", -(10**5000))
    assert len(str(caught.value)) < 80
    with pytest.raises(ValueError, match="an integer of 16610 bits"):
        build_ratelimit([ServiceLimit("a", 10**5000)])


def test_a_leap_second_outside_the_end_of_a_utc_day_says_so() -> None:
    with pytest.raises(RetryAfterError, match="leap second can only be 23:59:60 UTC"):
        parse_http_date("Sun, 06 Nov 1994 12:30:60 GMT")
    with pytest.raises(RetryAfterError, match="impossible date"):
        parse_http_date("Fri, 31 Dec 9999 23:59:60 GMT")

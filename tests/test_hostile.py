"""Hostile input: time grows linearly, messages stay short, odd types are refused cleanly."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest

from retryheader import (
    QuotaPolicy,
    ServiceLimit,
    build_ratelimit,
    build_ratelimit_policy,
    build_retry_after,
    delay_from_headers,
    format_http_date,
    parse_http_date,
    parse_ratelimit,
    parse_ratelimit_policy,
    parse_retry_after,
)

SHAPES: dict[str, Callable[[int], Callable[[], object]]] = {
    "spaces then a digit": lambda n: lambda: parse_retry_after(" " * n + "1"),
    "a long digit run": lambda n: lambda: parse_retry_after("9" * n),
    "digits then junk": lambda n: lambda: _quiet(parse_retry_after, "1" * n + "x"),
    "spaces inside a date": lambda n: (
        lambda: parse_http_date("Sun," + " " * n + "6 Nov 1994 08:49 GMT")
    ),
    "letters": lambda n: lambda: _quiet(parse_http_date, "a" * n),
    "many limits": lambda n: lambda: parse_ratelimit('"a";r=0, ' * (n // 9) + '"z";r=1'),
    "many parameters": lambda n: lambda: parse_ratelimit('"a";r=0' + ";k=1" * (n // 4)),
    "a long string": lambda n: lambda: parse_ratelimit('"' + "a" * n + '";r=0'),
    "a long byte sequence": lambda n: (
        lambda: parse_ratelimit('"a";r=0;pk=:' + "QUFB" * (n // 4) + ":")
    ),
    "a long inner list": lambda n: lambda: _quiet(parse_ratelimit, "(" + "1 " * (n // 2) + ")"),
    "many field lines": lambda n: lambda: parse_ratelimit(['"a";r=0'] * (n // 8)),
    "many headers": lambda n: lambda: delay_from_headers([("X-Y", "v")] * (n // 4)),
    "many Retry-After": lambda n: lambda: delay_from_headers([("Retry-After", "5")] * (n // 4)),
    "many RateLimit": lambda n: (
        lambda: delay_from_headers([("RateLimit", '"a";r=0;t=1')] * (n // 8))
    ),
    "building many limits": lambda n: lambda: build_ratelimit([ServiceLimit("a", 0, 5)] * (n // 8)),
}


def _quiet(function: Callable[[Any], object], value: Any) -> object:
    try:
        return function(value)
    except ValueError as error:
        return error


def _seconds(call: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        call()
        best = min(best, time.perf_counter() - start)
    return best


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_time_grows_linearly(shape: str) -> None:
    small, large = _seconds(SHAPES[shape](40_000)), _seconds(SHAPES[shape](320_000))
    # Eight times the input: linear work takes about 8 times as long, quadratic 64.
    assert large < 20 * small + 0.05, (shape, small, large)


HUGE = "x" * 1_000_000
BAD: list[Callable[[], object]] = [
    lambda: parse_retry_after(HUGE),
    lambda: parse_http_date(HUGE),
    lambda: parse_ratelimit('"' + HUGE + '";r=-1'),
    lambda: parse_ratelimit_policy('"a";q=1;' + "k" * 100_000 + "=@999999999999999"),
    lambda: build_ratelimit([ServiceLimit("a", 1, extra={"B" + HUGE: 1})]),
    lambda: build_ratelimit([ServiceLimit("\x01" + HUGE, 1)]),
    lambda: build_ratelimit([ServiceLimit("a", 1, extra={"x": "\x01" + HUGE})]),
    lambda: QuotaPolicy("a", -(10**100_000)),
    lambda: build_ratelimit([ServiceLimit("a", 10**100_000)]),
    lambda: build_retry_after(type("X" * 100_000, (), {})()),
    lambda: build_retry_after([0] * 1_000_000),  # type: ignore[arg-type]
    lambda: delay_from_headers(type("Y" * 100_000, (), {})()),
    lambda: ServiceLimit(type("Z" * 100_000, (str,), {})("a"), 1, extra={1: 2}),  # type: ignore[dict-item]
]


@pytest.mark.parametrize("index", range(len(BAD)))
def test_messages_stay_short_for_huge_input(index: int) -> None:
    with pytest.raises((TypeError, ValueError)) as caught:
        BAD[index]()
    assert len(str(caught.value)) <= 200


ODD: list[object] = [None, b"120", bytearray(b"1"), 120, True, 1.5, Decimal(1), [], object()]


@pytest.mark.parametrize("value", ODD, ids=[type(v).__name__ for v in ODD])
def test_odd_types_are_type_errors(value: object) -> None:
    for parse in (parse_retry_after, parse_http_date):
        with pytest.raises(TypeError):
            parse(value)  # type: ignore[arg-type]
    if not isinstance(value, list):
        for parse_field in (parse_ratelimit, parse_ratelimit_policy):
            with pytest.raises(TypeError):
                parse_field(value)  # type: ignore[arg-type]
    if not isinstance(value, (int, float, list)) or isinstance(value, bool):
        with pytest.raises(TypeError):
            build_retry_after(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        format_http_date(value)  # type: ignore[arg-type]
    if value is not None:  # None is the default: the current time
        with pytest.raises(TypeError):
            parse_retry_after("5", now=value)  # type: ignore[arg-type]


def test_builders_refuse_items_of_another_type() -> None:
    for build, item in ((build_ratelimit, QuotaPolicy("a", 1)), (build_ratelimit_policy, "a")):
        with pytest.raises(TypeError):
            build([item])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        delay_from_headers({"Retry-After": "5"}, now="now")  # type: ignore[arg-type]
    assert format_http_date(datetime(2026, 1, 1)) == "Thu, 01 Jan 2026 00:00:00 GMT"


def test_a_plain_date_as_now_is_refused_with_its_own_message() -> None:
    # A date is the easy mistake (date.today()); every now= refuses it before reading a field.
    day = date(2026, 1, 1)
    calls: list[Callable[[], object]] = [
        lambda: parse_retry_after("120", now=day),  # type: ignore[arg-type]
        lambda: parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT", now=day),  # type: ignore[arg-type]
        lambda: delay_from_headers({"Retry-After": "5"}, now=day),  # type: ignore[arg-type]
    ]
    for call in calls:
        with pytest.raises(TypeError, match=r"^expected a datetime, not date$"):
            call()


@pytest.mark.parametrize(
    ("length", "shown"),
    [(40, "N" * 40), (41, "N" * 37 + "..."), (200, "N" * 37 + "...")],
    ids=["40", "41", "200"],
)
def test_a_type_name_in_a_message_is_cut_to_40_characters(length: int, shown: str) -> None:
    odd = type("N" * length, (), {})()
    with pytest.raises(TypeError) as caught:
        format_http_date(odd)
    assert str(caught.value) == f"expected a datetime, not {shown}"

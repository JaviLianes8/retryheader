"""Contracts for the public value types: annotations, pickles and what they store."""

from __future__ import annotations

import enum
import inspect
import pickle
import typing
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

import retryheader
from retryheader import (
    DisplayString,
    QuotaPolicy,
    RateLimitError,
    ServiceLimit,
    Token,
    build_ratelimit,
    parse_ratelimit,
)

_MAX = 999_999_999_999_999


@pytest.mark.parametrize("name", retryheader.__all__)
def test_every_public_annotation_resolves(name: str) -> None:
    obj = getattr(retryheader, name)
    typing.get_type_hints(obj)
    if inspect.isclass(obj):
        typing.get_type_hints(obj.__init__)


def test_pydantic_can_validate_the_value_types() -> None:
    pydantic = pytest.importorskip("pydantic")
    policy = pydantic.TypeAdapter(QuotaPolicy).validate_python({"name": "a", "quota": 1})
    assert policy == QuotaPolicy("a", 1)


def _values() -> list[object]:
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    (parsed,) = parse_ratelimit('"a";r=1;mode=sliding;note=%"x";at=@1;b=:YQ==:;f=?1;d=1.5')
    return [
        QuotaPolicy("a", 1, 60, "content-bytes", b"k", {"x": 1.5, "at": at, "t": Token("t")}),
        ServiceLimit("a", 0, 5, b"k", {"flag": True, "s": DisplayString("café")}),
        parsed,
        Token("sliding"),
        DisplayString("x"),
        RateLimitError("bad"),
    ]


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_pickles_of_public_values_name_no_private_module(protocol: int) -> None:
    for value in _values():
        data = pickle.dumps(value, protocol=protocol)
        assert b"retryheader._" not in data, value
        clone = pickle.loads(data)
        assert type(clone) is type(value)
        if not isinstance(value, Exception):
            assert clone == value


def test_parsed_tokens_and_display_strings_are_the_public_types() -> None:
    (limit,) = parse_ratelimit('"a";r=1;mode=sliding;note=%"caf%c3%a9"')
    assert type(limit.extra["mode"]) is Token and limit.extra["mode"] == "sliding"
    assert type(limit.extra["note"]) is DisplayString and limit.extra["note"] == "café"
    assert Token.__module__ == DisplayString.__module__ == "retryheader"


def test_tokens_and_display_strings_are_built_in_their_own_form() -> None:
    limit = ServiceLimit("a", 1, extra={"m": Token("foo/bar"), "n": DisplayString("é")})
    assert build_ratelimit([limit]) == '"a";r=1;m=foo/bar;n=%"%c3%a9"'
    with pytest.raises(ValueError, match="invalid token"):
        build_ratelimit([ServiceLimit("a", 1, extra={"m": Token("no spaces")})])


@pytest.mark.parametrize(
    "text",
    ["a\ud800b", "\udfff", "x" * 60 + "\udc80", "x" * 10_000 + "\ud800"],
    ids=["inside", "alone", "after-60", "after-10000"],
)
def test_a_display_string_utf8_cannot_encode_is_the_librarys_value_error(text: str) -> None:
    limit = ServiceLimit("a", 1, extra={"m": DisplayString(text)})
    with pytest.raises(ValueError, match="display strings hold text UTF-8 can encode") as caught:
        build_ratelimit([limit])
    assert type(caught.value) is ValueError
    # The input is quoted cut to 40 characters, and the codec's error never shows in a traceback.
    assert len(str(caught.value)) < 120
    assert caught.value.__suppress_context__ is True


class _Hostile(str):
    def __repr__(self) -> str:
        return "HOSTILE"

    def __hash__(self) -> int:
        raise ZeroDivisionError


class _Level(enum.IntEnum):
    A = 5


class _Bytes(bytes):
    pass


class _Float(float):
    def __repr__(self) -> str:
        return "HOSTILE"


class _When(datetime):
    pass


def test_extra_values_are_stored_as_plain_builtins() -> None:
    at = _When(2026, 1, 1, tzinfo=timezone.utc)
    extra: dict[str, Any] = {
        "k": _Hostile("x"),
        "e": _Level.A,
        "b": _Bytes(b"z"),
        "f": _Float(0.5),
        "d": at,
    }
    extra["t"] = type("T", (Token,), {})("tok")
    limit = ServiceLimit("a", 0, extra=extra)
    types = {key: type(value) for key, value in limit.extra.items()}
    assert types == {"k": str, "e": int, "b": bytes, "f": float, "d": datetime, "t": Token}
    assert limit.extra == {"k": "x", "e": 5, "b": b"z", "f": 0.5, "d": at, "t": "tok"}
    assert "HOSTILE" not in repr(limit) and "_Level" not in repr(limit)
    assert hash(limit.extra) == hash(ServiceLimit("a", 0, extra=dict(limit.extra)).extra)
    assert type(QuotaPolicy("a", 1, extra={"k": _Hostile("x")}).extra["k"]) is str


@pytest.mark.parametrize("make", [lambda n: QuotaPolicy("a", n), lambda n: ServiceLimit("a", n)])
def test_counts_past_fifteen_digits_are_refused_on_creation(make: typing.Any) -> None:
    assert make(_MAX) is not None
    with pytest.raises(ValueError, match="at most 999999999999999"):
        make(_MAX + 1)
    with pytest.raises(ValueError, match="an integer of 16610 bits"):
        make(10**5000)


def test_windows_and_integer_extras_past_fifteen_digits_are_refused() -> None:
    with pytest.raises(ValueError, match="window must be at most"):
        ServiceLimit("a", 0, window=_MAX + 1)
    with pytest.raises(ValueError, match="window must be at most"):
        QuotaPolicy("a", 0, window=10**5000)
    for value in (_MAX + 1, -_MAX - 1, 10**5000):
        with pytest.raises(ValueError, match="15 digits"):
            ServiceLimit("a", 0, extra={"k": value})
    assert ServiceLimit("a", 0, extra={"k": -_MAX}).extra["k"] == -_MAX
    assert repr(ServiceLimit("a", _MAX, _MAX, extra={"k": _MAX}))


def test_a_date_parameter_reads_as_its_moment_and_round_trips() -> None:
    (limit,) = parse_ratelimit('"a";r=1;d=@1;e=@-86400')
    assert limit.extra["d"] == datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc)
    assert limit.extra["e"] == datetime(1969, 12, 31, tzinfo=timezone.utc)
    assert build_ratelimit([limit]) == '"a";r=1;d=@1;e=@-86400'
    later = datetime(2026, 10, 21, 7, 28, tzinfo=timezone(timedelta(hours=2)))
    built = build_ratelimit([ServiceLimit("a", 1, extra={"d": later})])
    assert built == '"a";r=1;d=@1792560480'
    assert parse_ratelimit(built)[0].extra["d"] == later

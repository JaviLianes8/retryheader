"""Independent implementations as oracles: http-sf, werkzeug and urllib3.

http-sf is the RFC 9651 reference implementation by one of its authors; werkzeug and
urllib3 read HTTP-dates and Retry-After for a large share of Python HTTP code. Each test
skips when its package is not installed (they are test-only, never dependencies).
"""

from __future__ import annotations

import base64
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from retryheader import format_http_date, parse_http_date, parse_retry_after
from retryheader._sf import parse_list
from retryheader._sf_scalars import SFError
from retryheader._sf_serialize import serialize_list
from retryheader._sf_types import Date, DisplayString, Token

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
FRAGMENTS = [
    '"a"',
    '"a\\"b"',
    "tok/x:y",
    "*t",
    "?1",
    "?0",
    "?2",
    "1",
    "-12",
    "1.5",
    "-0.25",
    "1.2345",
    "123456789012345",
    ":aGVsbG8=:",
    ":YQ==:",
    "@1659578233",
    "@-1",
    "@1.5",
    '%"f%c3%bc"',
    '%"%E2"',
    ";k",
    ";k=1",
    ";Kx=2",
    ";*k=?0",
    ", ",
    ",",
    "(",
    ")",
    "( 1 2 )",
    " ",
    "\t",
    "\x7f",
    "=",
    "a",
    "-",
    '"',
    "%",
    ":",
]


def _tag(value: Any, http_sf: Any) -> Any:
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (Token, http_sf.Token)):
        return ("token", str(value))
    if isinstance(value, (DisplayString, http_sf.DisplayString)):
        return ("display", str(value))
    if isinstance(value, (Date, datetime)):
        seconds = (
            value.seconds if isinstance(value, Date) else (value - EPOCH) // timedelta(seconds=1)
        )
        return ("date", seconds)
    if isinstance(value, (float, Decimal)):
        return ("decimal", Decimal(repr(value)) if isinstance(value, float) else value)
    return (type(value).__name__, value)


def _shape(members: Any, http_sf: Any) -> Any:
    def item(value: Any, params: dict[str, Any]) -> Any:
        return (_tag(value, http_sf), [(k, _tag(v, http_sf)) for k, v in params.items()])

    out = []
    for value, params in members:
        if isinstance(value, list):
            out.append(
                ([item(*i) for i in value], [(k, _tag(v, http_sf)) for k, v in params.items()])
            )
        else:
            out.append(item(value, params))
    return out


# Byte sequences are always padded here: RFC 9651 lets a parser refuse missing padding
# (the suite marks those cases can_fail) and http-sf does, while this parser accepts it.
@pytest.mark.parametrize("seed", [11, 12, 13])
def test_list_parsing_matches_http_sf(seed: int) -> None:
    http_sf = pytest.importorskip("http_sf")
    rng = random.Random(seed)
    agreed = 0
    for _ in range(6000):
        candidate = "".join(rng.choice(FRAGMENTS) for _ in range(rng.randrange(1, 7)))
        try:
            ours: Any = _shape(parse_list(candidate), http_sf)
        except SFError:
            ours = "fail"
        try:
            theirs: Any = _shape(http_sf.parse(candidate.encode(), tltype="list"), http_sf)
        except http_sf.StructuredFieldError:
            theirs = "fail"
        except (ValueError, OverflowError):
            continue  # a date the reference cannot hold as a datetime: a model limit
        assert ours == theirs, repr(candidate)
        agreed += ours != "fail"
    assert agreed > 500


@pytest.mark.parametrize("seed", [21, 22])
def test_list_serialisation_matches_http_sf(seed: int) -> None:
    http_sf = pytest.importorskip("http_sf")
    rng = random.Random(seed)

    def bare() -> Any:
        return rng.choice(
            [
                rng.randrange(-(10**15), 10**15),
                round(rng.uniform(-1e6, 1e6), rng.randrange(5)),
                "".join(rng.choice(' a"\\~') for _ in range(4)),
                Token(rng.choice(["a", "b/c", "*d"])),
                base64.b64decode("aGVsbG8="),
                rng.random() < 0.5,
                Date(rng.randrange(-(10**9), 10**9)),
                DisplayString(rng.choice(["fü", "%", 'q"'])),
            ]
        )

    def theirs(value: Any) -> Any:
        if isinstance(value, Token):
            return http_sf.Token(str(value))
        if isinstance(value, DisplayString):
            return http_sf.DisplayString(str(value))
        if isinstance(value, Date):
            return EPOCH + timedelta(seconds=value.seconds)
        return Decimal(repr(value)) if isinstance(value, float) else value

    for _ in range(3000):
        members = [(bare(), {rng.choice("abk*"): bare() for _ in range(rng.randrange(3))})]
        converted = [
            (theirs(v), {k: theirs(p) for k, p in params.items()}) for v, params in members
        ]
        assert serialize_list(members) == http_sf.ser(converted), members


def test_werkzeug_reads_and_writes_the_same_imf_fixdates() -> None:
    http = pytest.importorskip("werkzeug.http")
    rng = random.Random(31)
    for _ in range(3000):
        moment = EPOCH + timedelta(seconds=rng.randrange(-(10**9), 4 * 10**9))
        text = format_http_date(moment)
        assert text == http.http_date(moment)
        assert parse_http_date(text, strict=True) == http.parse_date(text) == moment


def test_urllib3_waits_as_long_for_seconds_and_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    retry = pytest.importorskip("urllib3.util.retry")
    now = datetime(2026, 10, 21, 7, 28, tzinfo=timezone.utc)
    monkeypatch.setattr(retry.time, "time", now.timestamp)
    policy = retry.Retry(retry_after_max=10**12)
    rng = random.Random(32)
    for _ in range(3000):
        seconds = rng.randrange(0, 10**7)
        assert parse_retry_after(str(seconds)) == policy.parse_retry_after(str(seconds))
        text = format_http_date(now + timedelta(seconds=rng.randrange(-(10**6), 10**8)))
        assert parse_retry_after(text, now=now) == policy.parse_retry_after(text)

"""Seeded random dates checked against independent parsers in the standard library."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime, parsedate_to_datetime
from http import cookiejar

from retryheader import build_retry_after, format_http_date, parse_http_date, parse_retry_after

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
NOW = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)


def _moments(count: int, seed: int) -> list[datetime]:
    rng = random.Random(seed)
    span = int((datetime(2075, 1, 1, tzinfo=timezone.utc) - EPOCH).total_seconds())
    return [EPOCH + timedelta(seconds=rng.randrange(span)) for _ in range(count)]


def test_imf_fixdate_matches_email_utils_both_ways() -> None:
    for moment in _moments(2000, seed=1):
        ours = format_http_date(moment)
        assert ours == format_datetime(moment, usegmt=True)
        assert parse_http_date(ours, strict=True) == parsedate_to_datetime(ours) == moment


def test_rfc850_matches_http2time() -> None:
    low, high = NOW.replace(year=1976), NOW.replace(year=2076)
    for moment in _moments(2000, seed=2):
        if not low < moment <= high:
            continue  # outside the window a two-digit year names another century
        text = moment.strftime("%A, %d-%b-%y %H:%M:%S GMT")
        assert parse_http_date(text, now=NOW, strict=True) == moment, text
        # http2time places two-digit years within 50 years of the real clock, so it
        # agrees for 1990 to 2060 whatever the current year is, up to 2040.
        if 1990 <= moment.year <= 2060:
            expected = (moment - EPOCH).total_seconds()
            assert cookiejar.http2time(text) == expected, text  # type: ignore[attr-defined]


def test_asctime_matches_email_utils() -> None:
    for moment in _moments(2000, seed=5):
        text = moment.strftime("%a %b ") + f"{moment.day:2d}" + moment.strftime(" %H:%M:%S %Y")
        assert parse_http_date(text, strict=True) == moment, text
        # email.utils returns asctime dates naive; RFC 9110 says they are UTC.
        assert parsedate_to_datetime(text).replace(tzinfo=timezone.utc) == moment


def test_build_then_parse_never_waits_less_than_asked() -> None:
    rng = random.Random(3)
    for _ in range(2000):
        seconds = rng.uniform(-10, 1e7)
        waited = parse_retry_after(build_retry_after(seconds))
        assert waited >= seconds
        assert waited - max(seconds, 0) < 1


def test_build_then_parse_a_datetime_never_lands_earlier() -> None:
    rng = random.Random(4)
    for _ in range(2000):
        moment = NOW + timedelta(microseconds=rng.randrange(10**13))
        waited = parse_retry_after(build_retry_after(moment), now=NOW)
        assert 0 <= waited - (moment - NOW).total_seconds() < 1

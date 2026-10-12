"""Regression tests for problems found in review."""

from __future__ import annotations

import copy
import dataclasses
import email
import http.client
import math
import pickle
from datetime import datetime, timedelta, timezone

import pytest

from retryheader import (
    QuotaPolicy,
    RetryAfterError,
    ServiceLimit,
    build_retry_after,
    delay_from_headers,
    format_http_date,
    parse_http_date,
    parse_ratelimit,
    parse_retry_after,
)

NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "value",
    [ServiceLimit("a", 1), ServiceLimit("a", 0, 5, b"k", extra={"x": 1}), QuotaPolicy("a", 1)],
)
def test_rate_limit_values_pickle_copy_and_convert(value: ServiceLimit | QuotaPolicy) -> None:
    assert pickle.loads(pickle.dumps(value)) == value
    assert copy.deepcopy(value) == value
    assert copy.copy(value) == value
    assert dataclasses.asdict(value)["extra"] == dict(value.extra)


def test_parsed_extra_survives_pickling_read_only() -> None:
    (limit,) = parse_ratelimit('"a";r=1;acme="x"')
    clone = pickle.loads(pickle.dumps(limit))
    assert dict(clone.extra) == {"acme": "x"}
    with pytest.raises(TypeError):
        clone.extra["acme"] = "y"
    with pytest.raises(TypeError):
        clone.extra.update(acme="y")


def test_http_client_headers_type_check_and_work() -> None:
    raw = b"Retry-After: 4\r\n\r\n"
    message = email.message_from_bytes(raw, _class=http.client.HTTPMessage)
    assert delay_from_headers(message) == 4.0


def test_a_huge_delay_is_documented_infinity() -> None:
    assert parse_retry_after("9" * 400) == math.inf
    assert delay_from_headers({"Retry-After": "9" * 400}) == math.inf
    assert "math.inf" in (parse_retry_after.__doc__ or "")


@pytest.mark.parametrize(
    "moment",
    [
        datetime(9999, 12, 31, 23, 59, 59, 500000),
        datetime(1, 1, 1, 0, 30, tzinfo=timezone(timedelta(hours=1))),
        datetime(9999, 12, 31, 23, 30, tzinfo=timezone(timedelta(hours=-1))),
    ],
)
def test_out_of_range_datetimes_are_value_errors(moment: datetime) -> None:
    with pytest.raises(ValueError):
        format_http_date(moment)
    with pytest.raises(ValueError):
        build_retry_after(moment)


def test_out_of_range_now_is_a_value_error() -> None:
    now = datetime(1, 1, 1, 0, 30, tzinfo=timezone(timedelta(hours=1)))
    with pytest.raises(ValueError):
        parse_retry_after("Sun, 06 Nov 1994 08:49:37 GMT", now=now)


def test_the_last_second_still_formats() -> None:
    assert format_http_date(datetime(9999, 12, 31, 23, 59, 59)).endswith("9999 23:59:59 GMT")


def test_a_delay_with_too_many_digits_raises_our_message() -> None:
    with pytest.raises(ValueError, match="too many digits"):
        build_retry_after(10**5000)


@pytest.mark.parametrize("strict", [True, False])
def test_a_leap_second_is_only_valid_at_the_end_of_a_utc_day(strict: bool) -> None:
    with pytest.raises(RetryAfterError):
        parse_http_date("Sun, 06 Nov 1994 12:30:60 GMT", strict=strict)


def test_a_leap_second_in_another_zone_is_checked_in_utc() -> None:
    parsed = parse_http_date("Fri, 01 Jan 2027 01:59:60 +0200")
    assert parsed == datetime(2027, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(RetryAfterError):
        parse_http_date("Thu, 31 Dec 2026 23:59:60 +0200")


@pytest.mark.parametrize(
    ("text", "year"),
    [
        ("6 Nov 49 08:49:37 +0000", 2049),
        ("6 Nov 50 08:49:37 +0000", 1950),
        ("6 Nov 94 08:49:37 +0000", 1994),
        ("6 Nov 126 08:49:37 +0000", 2026),
    ],
)
def test_lenient_rfc5322_years_follow_rfc5322(text: str, year: int) -> None:
    assert parse_http_date(text, now=NOW).year == year

"""Contracts for edge inputs: the reference time, odd subclasses, Age, Date and boundaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from retryheader import (
    RateLimitError,
    RetryAfterError,
    ServiceLimit,
    build_ratelimit,
    build_retry_after,
    delay_from_headers,
    format_http_date,
    parse_http_date,
    parse_ratelimit,
    parse_ratelimit_policy,
    parse_retry_after,
)

UTC = timezone.utc
IMF = "Sun, 06 Nov 1994 08:49:37 GMT"
RFC850 = "Sunday, 06-Nov-94 08:49:37 GMT"
# Aware moments whose UTC time falls outside years 1 to 9999.
NO_UTC = [
    datetime(1, 1, 1, 0, 30, tzinfo=timezone(timedelta(hours=1))),
    datetime(9999, 12, 31, 23, 30, tzinfo=timezone(timedelta(hours=-1))),
]
CALLS = [
    lambda now: parse_retry_after("5", now=now),
    lambda now: parse_retry_after(IMF, now=now),
    lambda now: parse_http_date(IMF, now=now),
    lambda now: parse_http_date(RFC850, now=now),
    lambda now: delay_from_headers({}, now=now),
    lambda now: delay_from_headers({"Retry-After": "5"}, now=now),
    lambda now: delay_from_headers({"Retry-After": IMF}, now=now),
    lambda now: delay_from_headers({"Date": RFC850}, now=now, use_date_header=True),
]


@pytest.mark.parametrize("now", NO_UTC)
@pytest.mark.parametrize("call", CALLS)
def test_a_now_without_a_utc_equivalent_is_one_value_error(now: datetime, call: Any) -> None:
    with pytest.raises(ValueError, match="now has no UTC equivalent") as caught:
        call(now)
    assert not isinstance(caught.value, RetryAfterError)


class _Fmt(datetime):
    def __format__(self, spec: str) -> str:
        return "08:49:37 GMT\r\nSet-Cookie: x=1\r\nX:"

    def weekday(self) -> int:
        return 99

    @property
    def year(self) -> int:
        return 12345


class _Days(int):
    def __str__(self) -> str:
        return "1\r\nSet-Cookie: a=b"


class _Delta(timedelta):
    @property
    def days(self) -> int:
        return _Days(1)


def test_datetime_and_timedelta_subclasses_are_read_as_their_values() -> None:
    hostile = _Fmt(1994, 11, 6, 8, 49, 37, tzinfo=UTC)
    assert format_http_date(hostile) == IMF
    assert build_retry_after(hostile) == IMF
    assert build_retry_after(_Delta(seconds=5)) == "5"
    assert parse_retry_after("Sun, 06 Nov 1994 08:49:47 GMT", now=hostile) == 10.0
    limit = ServiceLimit("a", 0, extra={"d": hostile})
    assert type(limit.extra["d"]) is datetime
    assert build_ratelimit([limit]) == '"a";r=0;d=@784111777'


@pytest.mark.parametrize(
    "headers",
    [
        {"Age": ", 5", "RateLimit": '"a";r=0;t=30'},
        {"Age": " ,\t, 7 ,x", "RateLimit": '"a";r=0;t=30'},
        [("Age", ""), ("Age", "5"), ("RateLimit", '"a";r=0;t=30')],
    ],
)
def test_the_first_non_empty_age_member_is_read(headers: Any) -> None:
    assert delay_from_headers(headers) is None


def test_an_empty_or_zero_age_keeps_the_ratelimit_fields() -> None:
    assert delay_from_headers({"Age": ", , ", "RateLimit": '"a";r=0;t=30'}) == 30.0
    assert delay_from_headers({"Age": ", 0, 5", "RateLimit": '"a";r=0;t=30'}) == 30.0


def test_the_date_header_counts_only_as_one_valid_field_line() -> None:
    now = datetime(2026, 10, 21, 7, 0, tzinfo=UTC)
    retry = ("Retry-After", "Wed, 21 Oct 2026 07:30:00 GMT")
    date = ("Date", "Wed, 21 Oct 2026 07:28:00 GMT")
    assert delay_from_headers([date, retry], now=now, use_date_header=True) == 120.0
    two = [date, ("Date", "junk"), retry]
    assert delay_from_headers(two, now=now, use_date_header=True) == 1800.0
    assert delay_from_headers([("Date", "junk"), retry], now=now, use_date_header=True) == 1800.0


@pytest.mark.parametrize(
    "text",
    [
        "Sun, 06 Nov 1994 08 : 49 : 37 GMT",
        "Sun, 06 Nov 1994 08\t:49:\t37 +0000",
        "6 Nov 1994 08 :49 GMT",
    ],
)
def test_the_obsolete_time_with_spaces_around_colons_is_read(text: str) -> None:
    expected = datetime(1994, 11, 6, 8, 49, 37 if "37" in text else 0, tzinfo=UTC)
    assert parse_http_date(text) == expected
    with pytest.raises(RetryAfterError):
        parse_http_date(text, strict=True)


def test_exactly_fifty_years_ahead_keeps_the_later_century() -> None:
    now = datetime(2060, 3, 5, 12, tzinfo=UTC)
    ahead = parse_http_date("Friday, 05-Mar-10 12:00:00 GMT", now=now)
    assert ahead == datetime(2110, 3, 5, 12, tzinfo=UTC)
    past = parse_http_date("Friday, 05-Mar-10 12:00:01 GMT", now=now)
    assert past == datetime(2010, 3, 5, 12, 0, 1, tzinfo=UTC)


def test_a_window_of_zero_is_written() -> None:
    assert build_ratelimit([ServiceLimit("a", 0, window=0)]) == '"a";r=0;t=0'
    assert parse_ratelimit('"a";r=0;t=0')[0].window == 0


@pytest.mark.parametrize("value", [":=:", ":==:", ":====:"])
def test_a_byte_sequence_of_padding_alone_is_malformed(value: str) -> None:
    with pytest.raises(RateLimitError):
        parse_ratelimit(f'"a";r=1;pk={value}')
    with pytest.raises(RateLimitError):
        parse_ratelimit_policy(f'"a";q=1;x={value}')


@pytest.mark.parametrize("value", ['\t"a";r=1', '\t "a";r=1', ' \t"a";r=1'])
def test_a_leading_tab_makes_the_field_malformed(value: str) -> None:
    with pytest.raises(RateLimitError):
        parse_ratelimit(value)
    with pytest.raises(RateLimitError):
        parse_ratelimit_policy(value.replace("r=", "q="))

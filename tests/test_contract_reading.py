"""Contracts on reading dates and fields: zone overflow, letter case, every line read."""

from __future__ import annotations

import email
import email.policy
from datetime import datetime, timezone

import pytest

from retryheader import (
    RateLimitError,
    RetryAfterError,
    delay_from_headers,
    parse_http_date,
    parse_ratelimit,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
NOV_6_1994 = datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", ["01 Jan 0001 00:30:00 +0100", "Fri, 31 Dec 9999 23:30:00 -0100"])
def test_a_zone_shift_past_the_calendar_is_a_retry_after_error(value: str) -> None:
    with pytest.raises(RetryAfterError):
        parse_http_date(value, now=NOW)
    assert delay_from_headers({"Retry-After": value}, now=NOW) is None


@pytest.mark.parametrize(
    "value",
    [
        "sunday, 06-nov-94 08:49:37 gmt",
        "SUNDAY, 06-NOV-94 08:49:37 GMT",
        "SUN NOV  6 08:49:37 1994",
        "sun nov  6 08:49:37 1994",
        "sun, 06 nov 1994 08:49:37 gmt",
    ],
)
def test_the_default_mode_reads_any_letter_case(value: str) -> None:
    assert parse_http_date(value, now=NOW) == NOV_6_1994


@pytest.mark.parametrize(
    "value",
    [
        "Sun, 06-Nov-94 08:49:37 GMT",
        "sunday, 06-nov-94 08:49:37 gmt",
        "SUN NOV  6 08:49:37 1994",
    ],
)
def test_strict_mode_rejects_a_short_rfc850_day_and_other_cases(value: str) -> None:
    with pytest.raises(RetryAfterError):
        parse_http_date(value, now=NOW, strict=True)


def test_an_invalid_retry_after_line_never_hides_a_later_valid_one() -> None:
    headers = [("Retry-After", "soon"), ("Retry-After", "30"), ("Retry-After", "x")]
    assert delay_from_headers(headers, now=NOW) == 30.0


def test_an_exhausted_limit_with_a_zero_window_waits_zero() -> None:
    assert delay_from_headers({"RateLimit": '"a";r=0;t=0'}, now=NOW) == 0.0


def test_the_date_header_resolves_two_digit_years_against_now() -> None:
    headers = {
        "Date": "Thursday, 01-Feb-80 00:00:00 GMT",
        "Retry-After": "Thu, 01 Feb 2080 00:02:00 GMT",
    }
    now = datetime(2100, 1, 1, tzinfo=timezone.utc)
    assert delay_from_headers(headers, now=now, use_date_header=True) == 120.0


@pytest.mark.parametrize(
    "field",
    [
        '"a";r=1;x=é',
        '"a";r=1;é=1',
        '"é";r=1',
        '"a";r=1;x="café"',
        '"a";r=1, é',
        '"a";r=1;x=té',
        '"a";r=1;x=1١',  # noqa: RUF001
    ],
)
def test_non_ascii_text_makes_a_ratelimit_field_malformed(field: str) -> None:
    with pytest.raises(RateLimitError):
        parse_ratelimit(field)


def test_a_malformed_non_ascii_ratelimit_field_is_ignored() -> None:
    assert delay_from_headers({"RateLimit": '"a";r=0;t=5;x=é'}, now=NOW) is None


def test_an_email_message_with_8bit_bytes_in_another_field_is_read() -> None:
    raw = b"Retry-After: 120\r\nX-Name: caf\xe9\r\n\r\n"
    message = email.message_from_bytes(raw)
    assert delay_from_headers(message, now=NOW) == 120.0
    modern = email.message_from_bytes(raw, policy=email.policy.default)
    assert delay_from_headers(modern, now=NOW) == 120.0


def test_an_8bit_retry_after_in_an_email_message_is_ignored() -> None:
    raw = b'Retry-After: 3\xe9\r\nRetry-After: 7\r\nRateLimit: "a";r=0;t=9\xe9\r\n\r\n'
    assert delay_from_headers(email.message_from_bytes(raw), now=NOW) == 7.0
    raw = b'RateLimit: "a";r=0;t=9\xe9\r\n\r\n'
    assert delay_from_headers(email.message_from_bytes(raw), now=NOW) is None

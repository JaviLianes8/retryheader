from datetime import datetime, timedelta, timezone

import pytest

from retryheader import RetryAfterError, parse_retry_after

NOW = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)


def test_delta_seconds_parses_to_float() -> None:
    assert parse_retry_after("120") == 120.0


def test_delta_seconds_ignores_surrounding_whitespace() -> None:
    assert parse_retry_after("  5 ") == 5.0


def test_http_date_resolves_against_now() -> None:
    value = "Wed, 21 Oct 2026 07:30:00 GMT"
    assert parse_retry_after(value, now=NOW) == 120.0


def test_http_date_in_the_past_clamps_to_zero() -> None:
    value = "Wed, 21 Oct 2026 07:00:00 GMT"
    assert parse_retry_after(value, now=NOW) == 0.0


def test_naive_now_is_read_as_utc() -> None:
    naive = NOW.replace(tzinfo=None)
    value = "Wed, 21 Oct 2026 07:29:00 GMT"
    assert parse_retry_after(value, now=naive) == 60.0


def test_default_now_uses_the_current_time() -> None:
    soon = datetime.now(timezone.utc) + timedelta(seconds=30)
    value = soon.strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert 0.0 < parse_retry_after(value) <= 30.0


def test_empty_value_raises() -> None:
    with pytest.raises(RetryAfterError):
        parse_retry_after("   ")


def test_malformed_value_raises() -> None:
    with pytest.raises(RetryAfterError):
        parse_retry_after("not a date")


def test_negative_number_is_not_valid_delta_seconds() -> None:
    with pytest.raises(RetryAfterError):
        parse_retry_after("-5")

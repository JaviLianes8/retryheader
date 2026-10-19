from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from retryheader import RetryAfterError, parse_retry_after
from tests.fixtures_text import CITED_RETRY_AFTER, rfc9110_retry_after

NOW = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
BEFORE = datetime(1999, 12, 31, 23, 57, 59, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", CITED_RETRY_AFTER)
def test_the_cited_rfc9110_examples_wait_two_minutes(value: str) -> None:
    # "In the latter example, the delay is 2 minutes"; the date is two minutes after BEFORE.
    assert parse_retry_after(value, now=BEFORE, strict=True) == 120.0


def test_every_rfc9110_example_in_the_fetched_text_parses() -> None:
    examples = rfc9110_retry_after()
    assert examples == CITED_RETRY_AFTER
    for value in examples:
        assert parse_retry_after(value, now=BEFORE, strict=True) == 120.0


def test_delta_seconds_parses_to_float() -> None:
    assert parse_retry_after("120") == 120.0


def test_leading_zeros_are_digits_too() -> None:
    assert parse_retry_after("007") == 7.0
    assert parse_retry_after("0") == 0.0


def test_a_huge_delay_is_infinite_not_an_error() -> None:
    assert parse_retry_after("9" * 5000) == float("inf")


def test_spaces_and_tabs_around_the_value_are_ignored() -> None:
    assert parse_retry_after("  5 ") == 5.0
    assert parse_retry_after("\t5\t") == 5.0


@pytest.mark.parametrize(
    "value",
    ["-5", "+5", "1.5", "1e3", "5 s", "1 2", "١٢", "\n5", "5\r\n", "120, 120", "0x10"],
)
def test_anything_but_ascii_digits_is_not_delay_seconds(value: str) -> None:
    with pytest.raises(RetryAfterError):
        parse_retry_after(value)


def test_http_date_resolves_against_now() -> None:
    assert parse_retry_after("Wed, 21 Oct 2026 07:30:00 GMT", now=NOW) == 120.0


def test_every_http_date_format_is_accepted() -> None:
    assert parse_retry_after("Wednesday, 21-Oct-26 07:30:00 GMT", now=NOW) == 120.0
    assert parse_retry_after("Wed Oct 21 07:30:00 2026", now=NOW) == 120.0


def test_http_date_in_the_past_clamps_to_zero() -> None:
    assert parse_retry_after("Wed, 21 Oct 2026 07:00:00 GMT", now=NOW) == 0.0


def test_naive_now_is_read_as_utc() -> None:
    naive = NOW.replace(tzinfo=None)
    assert parse_retry_after("Wed, 21 Oct 2026 07:29:00 GMT", now=naive) == 60.0


def test_aware_now_in_another_zone_is_converted() -> None:
    local = NOW.astimezone(timezone(timedelta(hours=-5)))
    assert parse_retry_after("Wed, 21 Oct 2026 07:29:00 GMT", now=local) == 60.0


def test_sub_second_precision_of_now_is_kept() -> None:
    now = NOW + timedelta(milliseconds=250)
    assert parse_retry_after("Wed, 21 Oct 2026 07:28:01 GMT", now=now) == 0.75


def test_default_now_uses_the_current_time() -> None:
    soon = datetime.now(timezone.utc) + timedelta(seconds=30)
    value = soon.strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert 0.0 < parse_retry_after(value) <= 30.0


def test_strict_mode_rejects_numeric_zones() -> None:
    value = "Wed, 21 Oct 2026 09:30:00 +0200"
    assert parse_retry_after(value, now=NOW) == 120.0
    with pytest.raises(RetryAfterError):
        parse_retry_after(value, now=NOW, strict=True)


def test_a_date_without_a_zone_is_rejected() -> None:
    with pytest.raises(RetryAfterError):
        parse_retry_after("Wed, 21 Oct 2026 07:30:00", now=NOW)


def test_empty_value_raises() -> None:
    with pytest.raises(RetryAfterError):
        parse_retry_after("   ")


def test_malformed_value_raises_with_the_value_in_the_message() -> None:
    with pytest.raises(RetryAfterError, match="not a date"):
        parse_retry_after("not a date")


def test_non_string_values_are_type_errors() -> None:
    with pytest.raises(TypeError):
        parse_retry_after(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_retry_after(b"120")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_retry_after("120", now=0)  # type: ignore[arg-type]

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from retryheader import RetryAfterError, format_http_date, parse_http_date
from tests.fixtures_text import rfc9110_dates

NOW = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
EXAMPLE = datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc)


@pytest.mark.parametrize("text", rfc9110_dates())
def test_every_rfc9110_example_format_parses_to_the_same_moment(text: str) -> None:
    assert parse_http_date(text, now=NOW, strict=True) == EXAMPLE


def test_the_result_is_aware_utc() -> None:
    parsed = parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT")
    assert parsed.utcoffset() == timedelta(0)


def test_asctime_accepts_a_two_digit_day() -> None:
    assert parse_http_date("Sun Nov 16 08:49:37 1994").day == 16


@pytest.mark.parametrize(
    ("yy", "now_year", "expected"),
    [
        ("60", 2026, 2060),  # 34 years ahead: not more than 50, so the future century
        ("76", 2026, 2076),  # exactly 50 years ahead, same moment: still not more than 50
        ("77", 2026, 1977),  # 51 years ahead: the most recent past year ending in 77
        ("94", 2026, 1994),
        ("05", 2095, 2105),  # 10 years ahead of 2095, not 90 years back
        ("26", 2026, 2026),
    ],
)
def test_rfc850_two_digit_years_follow_the_50_year_rule(
    yy: str, now_year: int, expected: int
) -> None:
    now = datetime(now_year, 11, 6, 8, 49, 37, tzinfo=timezone.utc)
    text = f"Sunday, 06-Nov-{yy} 08:49:37 GMT"
    assert parse_http_date(text, now=now).year == expected


def test_the_50_year_rule_counts_to_the_second() -> None:
    now = datetime(2026, 11, 6, 8, 49, 36, tzinfo=timezone.utc)
    assert parse_http_date("Sunday, 06-Nov-76 08:49:37 GMT", now=now).year == 1976


def test_a_leap_second_is_the_next_second() -> None:
    parsed = parse_http_date("Thu, 31 Dec 2026 23:59:60 GMT")
    assert parsed == datetime(2027, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "text",
    [
        "Mon, 30 Feb 2026 00:00:00 GMT",
        "Mon, 01 Jan 2026 24:00:00 GMT",
        "Mon, 01 Jan 2026 00:60:00 GMT",
        "Mon, 01 Jan 2026 00:00:61 GMT",
        "Mon, 00 Jan 2026 00:00:00 GMT",
        "Fri, 31 Dec 9999 23:59:60 GMT",
    ],
)
def test_impossible_dates_are_rejected(text: str) -> None:
    with pytest.raises(RetryAfterError):
        parse_http_date(text)


@pytest.mark.parametrize(
    "text",
    [
        "sun, 06 nov 1994 08:49:37 gmt",
        "Sun,  06 Nov 1994 08:49:37 GMT",
        "Sun, 6 Nov 1994 08:49:37 GMT",
        "Sun, 06 Nov 1994 10:49:37 +0200",
        "Sun, 06 Nov 1994 08:49:37 UTC",
        "Sun, 06 Nov 1994 03:49:37 EST",
        "06 Nov 1994 08:49:37 GMT",
    ],
)
def test_lenient_mode_accepts_dates_with_an_explicit_zone(text: str) -> None:
    assert parse_http_date(text) == EXAMPLE
    with pytest.raises(RetryAfterError):
        parse_http_date(text, strict=True)


@pytest.mark.parametrize(
    "text",
    [
        "Sun, 06 Nov 1994 08:49:37",
        "Sun, 06 Nov 1994 08:49:37 XYZ",
        "Sun, 06 Nov 1994 08:49:37 Z",
        "Sun, 06 Nov 1994 08:49:37 +0260",
        "1994-11-06T08:49:37Z",
        "Sun, 06 Nov 1994 08:49:37 GMT trailing",
        "",
    ],
)
def test_dates_without_a_known_zone_or_with_junk_are_rejected(text: str) -> None:
    with pytest.raises(RetryAfterError):
        parse_http_date(text)


def test_surrounding_spaces_and_tabs_are_ignored() -> None:
    assert parse_http_date(" \tSun, 06 Nov 1994 08:49:37 GMT\t ", strict=True) == EXAMPLE


def test_a_non_string_is_a_type_error() -> None:
    with pytest.raises(TypeError):
        parse_http_date(None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT", now="now")  # type: ignore[arg-type]


def test_format_renders_imf_fixdate() -> None:
    assert format_http_date(EXAMPLE) == "Sun, 06 Nov 1994 08:49:37 GMT"


def test_format_converts_other_zones_and_reads_naive_as_utc() -> None:
    plus_two = timezone(timedelta(hours=2))
    assert format_http_date(EXAMPLE.astimezone(plus_two)) == "Sun, 06 Nov 1994 08:49:37 GMT"
    assert format_http_date(EXAMPLE.replace(tzinfo=None)) == "Sun, 06 Nov 1994 08:49:37 GMT"


def test_format_rounds_a_fraction_of_a_second_up() -> None:
    assert format_http_date(EXAMPLE.replace(microsecond=1)) == "Sun, 06 Nov 1994 08:49:38 GMT"


def test_format_pads_years_to_four_digits() -> None:
    assert format_http_date(datetime(999, 1, 1)) == "Tue, 01 Jan 0999 00:00:00 GMT"


def test_format_rejects_non_datetimes() -> None:
    with pytest.raises(TypeError):
        format_http_date("2026-10-21")  # type: ignore[arg-type]

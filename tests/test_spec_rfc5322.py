"""The robust mode against RFC 5322 as fetched: zones, years and its verified erratum 6639.

RFC 9110 asks recipients to be robust with timestamps that come from other sources, such
as the Internet Message Format, so the default mode reads RFC 5322 dates that carry a
zone whose offset is known. These tests read that knowledge from the RFC text.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone

import pytest

from retryheader import RetryAfterError, parse_http_date
from tests.upstream_files import UPSTREAM, read, section, sentence, text

RFC5322 = "rfc5322.txt"
ERRATUM = "rfc5322-erratum-6639.html"
NOW = datetime(2026, 10, 21, tzinfo=timezone.utc)
BASE = "Sun, 06 Nov 1994 08:49:37"
MOMENT = datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc)


def _obsolete() -> str:
    return section(text(RFC5322), "4.3.  Obsolete Date and Time")


def test_every_named_us_zone_has_the_offset_the_rfc_gives() -> None:
    table = re.findall(r"([ECMP][SD]T) is semantically equivalent to ([+-]\d{4})", _obsolete())
    assert len(table) == 8
    for zone, offset in table:
        assert parse_http_date(f"{BASE} {zone}") == parse_http_date(f"{BASE} {offset}"), zone
        hours = int(offset[1:3]) * (-1 if offset[0] == "-" else 1)
        assert parse_http_date(f"{BASE} {zone}") == MOMENT - timedelta(hours=hours)


def test_ut_and_gmt_are_universal_time() -> None:
    assert 'semantically identical to "+0000"' in sentence(_obsolete(), "both semantically")
    for zone in ("UT", "GMT", "+0000", "-0000"):
        assert parse_http_date(f"{BASE} {zone}") == MOMENT


def test_military_and_unknown_zones_are_refused_rather_than_guessed() -> None:
    # The RFC says to read them as -0000 (time in UT, local zone unknown). Here a wrong
    # zone would silently shift a delay by hours, so they are refused instead.
    military = sentence(_obsolete(), "SHOULD all be considered equivalent")
    assert '"-0000"' in military
    for zone in ("Z", "A", "M", "N", "Y", "CET", "BST", "XYZ"):
        with pytest.raises(RetryAfterError):
            parse_http_date(f"{BASE} {zone}")


@pytest.mark.parametrize(("year", "expected"), [("00", 2000), ("49", 2049), ("50", 1950)])
def test_two_digit_years_follow_section_4_3(year: str, expected: int) -> None:
    rule = sentence(_obsolete(), "two digit year is encountered whose")
    assert "between 00 and 49" in rule and "adding 2000" in rule
    assert parse_http_date(f"6 Nov {year} 08:49:37 +0000", now=NOW).year == expected


def test_three_digit_years_count_from_1900() -> None:
    assert "any three digit year" in sentence(_obsolete(), "any three digit year")
    assert parse_http_date("6 Nov 126 08:49:37 +0000", now=NOW).year == 2026


def test_zone_minutes_stop_at_59_and_hours_may_reach_99() -> None:
    body = section(text(RFC5322), "3.3.  Date and Time Specification")
    semantic = sentence(body, "the last two digits of the zone")
    assert "last two digits of the zone MUST be within the range 00 through 59" in semantic
    assert parse_http_date(f"{BASE} +9959") == MOMENT - timedelta(hours=99, minutes=59)
    with pytest.raises(RetryAfterError):
        parse_http_date(f"{BASE} +0060")


def test_erratum_6639_lets_a_named_zone_follow_without_a_space() -> None:
    if not (UPSTREAM / ERRATUM).is_file():
        pytest.skip("upstream files are not fetched; run python scripts/fetch_upstream.py")
    page = html.unescape(re.sub(r"<[^>]+>", " ", read(ERRATUM).decode("utf-8")))
    flat = re.sub(r"\s+", " ", page)
    assert "Verified" in flat
    assert 'zone = (FWS ( "+" / "-" ) 4DIGIT) / [FWS] obs-zone' in flat
    assert parse_http_date(f"{BASE}GMT") == parse_http_date(f"{BASE} GMT") == MOMENT
    with pytest.raises(RetryAfterError):
        parse_http_date(f"{BASE}+0000")  # a numeric zone still needs its space

"""RFC 9110 as fetched: its grammar and sentences, read from the text, judge the parser.

The HTTP-date, delay-seconds and OWS rules are converted from the fetched ABNF into
regular expressions (tests/abnf.py); the meaning of the fields (calendar dates, the day
name, leap seconds, two-digit years) is computed here from datetime alone. Seeded random
candidates, valid and broken, must be accepted by the strict parser exactly when the
grammar and those meanings say so.
"""

from __future__ import annotations

import random
import re
from datetime import datetime, timedelta, timezone

import pytest

from retryheader import RetryAfterError, parse_http_date, parse_retry_after
from tests.abnf import rules, to_regex
from tests.fixtures_text import RFC9110
from tests.upstream_files import section, sentence, text

NOW = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _grammar() -> dict[str, str]:
    body = text(RFC9110)
    found = rules(section(body, "5.6.7.  Date/Time Formats"))
    found.update(rules(section(body, "10.2.3.  Retry-After")))
    found.update(rules(section(body, "5.6.3.  Whitespace")))
    return found


def _expected(candidate: str, formats: dict[str, re.Pattern[str]]) -> datetime | None:
    """What RFC 9110 says the strict parser must return, or None for a refusal."""
    # Section 5.5: a field value excludes the optional whitespace around it.
    candidate = candidate.strip(" \t")
    kind = next((k for k, pattern in formats.items() if pattern.fullmatch(candidate)), None)
    if kind is None:
        return None
    numbers = [int(n) for n in re.findall(r"\d+", candidate)]
    month = MONTHS.index(re.findall(r"[A-Z][a-z]{2}", candidate)[1]) + 1
    if kind == "imf":
        day, year, hour, minute, second = numbers
    elif kind == "rfc850":
        day, yy, hour, minute, second = numbers
        year = _fifty_year_rule(yy, (month, day, hour, minute, second))
    else:
        day, hour, minute, second, year = numbers
    try:
        local = datetime(year, month, day, hour, minute, min(second, 59), tzinfo=timezone.utc)
    except ValueError:
        return None
    if DAYS[local.weekday()][:3] != candidate[:3]:
        return None
    if second == 60:
        if (hour, minute) != (23, 59) or (year, month, day) == (9999, 12, 31):
            return None
        return local + timedelta(seconds=1)
    return local if second < 60 else None


def _fifty_year_rule(yy: int, rest: tuple[int, int, int, int, int]) -> int:
    # "more than 50 years in the future" is read as later than NOW plus 50 years.
    limit = (NOW.year + 50, NOW.month, NOW.day, NOW.hour, NOW.minute, NOW.second)
    candidates = [century + yy for century in range(0, 10100, 100)]
    return max(year for year in candidates if (year, *rest) <= limit)


def _candidates(seed: int, count: int) -> list[str]:
    rng = random.Random(seed)
    out = []
    for _ in range(count):
        year, month, day = rng.randrange(1, 10000), rng.randrange(1, 13), rng.randrange(0, 33)
        clock = (
            f"{rng.randrange(25):02d}:{rng.randrange(61):02d}:{rng.choice([0, 30, 59, 60, 61]):02d}"
        )
        if rng.random() < 0.3:
            clock = "23:59:60"
        name = DAYS[rng.randrange(7)]
        if rng.random() < 0.7 and 1 <= day <= 28:
            name = DAYS[datetime(year, month, day).weekday()]
        mon = MONTHS[month - 1]
        out += [
            f"{name[:3]}, {day:02d} {mon} {year:04d} {clock} GMT",
            f"{name}, {day:02d}-{mon}-{year % 100:02d} {clock} GMT",
            f"{name[:3]} {mon} {day:2d} {clock} {year:04d}",
        ]
    for _ in range(count):
        chars = list(rng.choice(out))
        for _ in range(rng.randrange(1, 3)):
            spot = rng.randrange(len(chars) + 1)
            choice = rng.choice(["ins", "del", "case"])
            if choice == "ins":
                chars.insert(spot, rng.choice(" \t0,-:aAzZ9"))
            elif choice == "del" and chars:
                del chars[min(spot, len(chars) - 1)]
            elif chars:
                index = min(spot, len(chars) - 1)
                chars[index] = chars[index].swapcase()
        out.append("".join(chars))
    return out


def test_the_grammar_is_read_from_the_text() -> None:
    grammar = _grammar()
    assert grammar["delay-seconds"] == "1*DIGIT"
    assert grammar["OWS"] == "*( SP / HTAB )"
    assert grammar["HTTP-date"] == "IMF-fixdate / obs-date"
    assert to_regex("delay-seconds", grammar) == "(?:(?:[0-9]){1,})"


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_strict_mode_accepts_exactly_what_the_rfc_allows(seed: int) -> None:
    grammar = _grammar()
    formats = {
        kind: re.compile(to_regex(rule, grammar))
        for kind, rule in (
            ("imf", "IMF-fixdate"),
            ("rfc850", "rfc850-date"),
            ("asctime", "asctime-date"),
        )
    }
    accepted = 0
    for candidate in _candidates(seed, 4000):
        expected = _expected(candidate, formats)
        try:
            actual = parse_http_date(candidate, now=NOW, strict=True)
        except RetryAfterError:
            actual = None
        assert actual == expected, candidate
        accepted += actual is not None
        if expected is not None:
            # The default mode accepts everything the strict one does.
            assert parse_http_date(candidate, now=NOW) == expected, candidate
    assert accepted > 2000


@pytest.mark.parametrize("seed", [4, 5])
def test_delay_seconds_is_exactly_the_rule_after_optional_whitespace(seed: int) -> None:
    grammar = _grammar()
    delay = re.compile(to_regex("delay-seconds", grammar))
    ows = re.compile(to_regex("OWS", grammar))
    rng = random.Random(seed)
    for _ in range(20000):
        candidate = "".join(
            rng.choice("0123456789 \t\n\r+-.e\u0661\u00a0x,") for _ in range(rng.randrange(6))
        )
        stripped = candidate.strip(" \t")
        assert ows.fullmatch(candidate[: len(candidate) - len(candidate.lstrip(" \t"))])
        expected = float(stripped) if delay.fullmatch(stripped) else None
        try:
            actual: float | None = parse_retry_after(candidate)
        except RetryAfterError:
            actual = None
        assert actual == expected, repr(candidate)


def test_the_sentences_the_parser_follows_are_in_the_text() -> None:
    body = section(text(RFC9110), "5.6.7.  Date/Time Formats")
    assert "MUST accept all three HTTP-date formats" in sentence(body, "MUST accept all three")
    rule = sentence(body, "more than 50 years in the future")
    assert "most recent year in the past that had the same last two digits" in rule
    flat = re.sub(r"\s+", " ", body)
    assert "HTTP-date is case sensitive." in flat
    assert "values in the asctime format are assumed to be in UTC" in flat
    retry = section(text(RFC9110), "10.2.3.  Retry-After")
    assert "the delay is 2 minutes" in re.sub(r"\s+", " ", retry)


def test_http_date_is_case_sensitive_only_in_strict_mode() -> None:
    lower = "sun, 06 nov 1994 08:49:37 gmt"
    assert parse_http_date(lower) == datetime(1994, 11, 6, 8, 49, 37, tzinfo=timezone.utc)
    with pytest.raises(RetryAfterError):
        parse_http_date(lower, strict=True)

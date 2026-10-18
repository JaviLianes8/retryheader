"""draft-ietf-httpapi-ratelimit-headers-11 as fetched: each requirement the parsers rely
on is located in the text, then exercised."""

from __future__ import annotations

import pytest

from retryheader import (
    RateLimitError,
    build_ratelimit,
    build_ratelimit_policy,
    delay_from_headers,
    parse_ratelimit,
    parse_ratelimit_policy,
)
from tests.fixtures_text import DRAFT, draft_fields
from tests.upstream_files import section, sentence, text


def _sentence(heading: str, words: str) -> str:
    return sentence(section(text(DRAFT), heading), words)


def test_the_policy_field_is_a_non_empty_list_of_string_items() -> None:
    rule = _sentence("3.  RateLimit-Policy Field", "non-empty List")
    assert "non-empty List[SF] of Quota Policy Items" in rule
    assert "MUST be a String[SF]" in _sentence("3.  RateLimit-Policy Field", "Item[SF] value")
    with pytest.raises(RateLimitError):
        parse_ratelimit_policy("")
    for value in ("burst;q=1", '%"burst";q=1', "1;q=1", ":YQ==:;q=1"):
        with pytest.raises(RateLimitError):
            parse_ratelimit_policy(value)


@pytest.mark.parametrize(
    ("heading", "words", "bad"),
    [
        ("3.1.1.  Quota Parameter", "MUST be a non-negative Integer", ["-1", "1.0", '"1"', "?1"]),
        ("3.1.3.  Window Parameter", "non-negative, non-zero", ["0", "-1", "1.5", '"60"']),
        ("3.1.2.  Quota Unit Parameter", "The value MUST be a String", ["requests", '%"x"', "1"]),
        ("3.1.4.  Partition Key Parameter", "MUST be a Byte Sequence", ['"k"', "k", "?1"]),
    ],
)
def test_policy_parameters_follow_the_draft(heading: str, words: str, bad: list[str]) -> None:
    assert words in _sentence(heading, words)
    name = {"3.1.1.": "q", "3.1.3.": "w", "3.1.2.": "qu", "3.1.4.": "pk"}[heading[:6]]
    for value in bad:
        field = f'"p";{name}={value}' if name == "q" else f'"p";q=1;{name}={value}'
        with pytest.raises(RateLimitError):
            parse_ratelimit_policy(field)


def test_q_is_required_and_qu_defaults_to_requests() -> None:
    assert "REQUIRED" in _sentence("3.1.  Quota Policy Item", "indicates the quota allocated")
    assert '"requests"' in _sentence("3.1.  Quota Policy Item", "The default quota unit")
    with pytest.raises(RateLimitError):
        parse_ratelimit_policy('"p";w=60')
    assert parse_ratelimit_policy('"p";q=0')[0].unit == "requests"


@pytest.mark.parametrize(
    ("heading", "words", "name", "bad"),
    [
        ("4.1.1.  Available Quota Parameter", "non-negative Integer", "r", ["-1", "1.5", '"1"']),
        ("4.1.2.  Effective Window Parameter", "non-negative Integer", "t", ["-1", "2.5", "?0"]),
        ("4.1.3.  Partition Key Parameter", "MUST be a Byte Sequence", "pk", ['"k"', "k"]),
    ],
)
def test_limit_parameters_follow_the_draft(
    heading: str, words: str, name: str, bad: list[str]
) -> None:
    assert words in _sentence(heading, words)
    for value in bad:
        field = f'"p";{name}={value}' if name == "r" else f'"p";r=1;{name}={value}'
        with pytest.raises(RateLimitError):
            parse_ratelimit(field)
    assert parse_ratelimit('"p";r=0;t=0')[0].window == 0


def test_r_is_required_and_other_parameters_are_kept() -> None:
    assert "REQUIRED" in _sentence("4.1.  Service Limit Item", "conveys the available quota")
    assert "regarded as comments" in _sentence("4.1.  Service Limit Item", "Other parameters")
    with pytest.raises(RateLimitError):
        parse_ratelimit('"p";t=5')
    (limit,) = parse_ratelimit('"p";r=1;acme-burst=5')
    assert dict(limit.extra) == {"acme-burst": 5}


def test_a_list_split_over_field_lines_is_one_list() -> None:
    assert "split over multiple" in _sentence("4.  RateLimit Field", "split over multiple")
    assert [lim.policy for lim in parse_ratelimit(['"a";r=1', '"b";r=2'])] == ["a", "b"]


def test_client_behaviour_sentences_drive_delay_from_headers() -> None:
    client = section(text(DRAFT), "7.  Client Behavior")
    assert "Malformed RateLimit header fields MUST be ignored" in sentence(client, "Malformed")
    precedence = sentence(client, "MUST take precedence")
    assert "the Retry-After field MUST take precedence" in precedence
    assert delay_from_headers({"RateLimit": '"a";r=0;t=9;q=x;q=?', "Retry-After": "x"}) is None
    assert delay_from_headers({"RateLimit": '"a";r=0;t=9', "Retry-After": "3"}) == 3.0
    caching = sentence(section(text(DRAFT), "7.3.  Caching"), "SHOULD be ignored")
    assert "responses that come from cache" in caching
    assert delay_from_headers({"RateLimit": '"a";r=0;t=9', "Age": "60"}) is None


def test_every_example_rebuilds_to_the_same_values() -> None:
    for value in draft_fields("RateLimit-Policy"):
        policies = parse_ratelimit_policy(value)
        assert parse_ratelimit_policy(build_ratelimit_policy(policies)) == policies
    for value in draft_fields("RateLimit"):
        limits = parse_ratelimit(value)
        assert parse_ratelimit(build_ratelimit(limits)) == limits

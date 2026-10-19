from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

import pytest

from retryheader import (
    QuotaPolicy,
    RateLimitError,
    ServiceLimit,
    parse_ratelimit,
    parse_ratelimit_policy,
)
from tests.fixtures_text import CITED_LIMITS, CITED_POLICIES, draft_fields


@pytest.mark.parametrize("value", CITED_POLICIES)
def test_the_cited_policy_examples_parse(value: str) -> None:
    assert parse_ratelimit_policy(value)


@pytest.mark.parametrize("value", CITED_LIMITS)
def test_the_cited_limit_examples_parse(value: str) -> None:
    assert parse_ratelimit(value)


def test_every_example_in_the_fetched_draft_parses() -> None:
    policies, limits = draft_fields("RateLimit-Policy"), draft_fields("RateLimit")
    assert (len(policies), len(limits)) == (17, 23)
    assert set(CITED_POLICIES) <= set(policies)
    assert set(CITED_LIMITS) <= set(limits)
    for value in policies:
        assert parse_ratelimit_policy(value), value
    for value in limits:
        assert parse_ratelimit(value), value


def test_policies_carry_every_defined_parameter() -> None:
    value = '"peruser";q=65535;qu="content-bytes";w=10;pk=:sdfjLJUOUH==:'
    (policy,) = parse_ratelimit_policy(value)
    assert policy.name == "peruser"
    assert policy.quota == 65535
    assert policy.unit == "content-bytes"
    assert policy.window == 10
    assert policy.partition_key == bytes.fromhex("b1d7e32c950e50")
    assert dict(policy.extra) == {}


def test_policy_defaults_and_order() -> None:
    value = '"burst";q=100;w=60,"daily";q=1000;w=86400, "open";q=5'
    assert parse_ratelimit_policy(value) == [
        QuotaPolicy("burst", 100, 60),
        QuotaPolicy("daily", 1000, 86400),
        QuotaPolicy("open", 5, None, "requests"),
    ]


def test_limits_carry_every_defined_parameter() -> None:
    (limit,) = parse_ratelimit('"default";r=300000000;t=60;pk=:QXBwLTk5OQ==:')
    assert limit == ServiceLimit("default", 300000000, 60, b"App-999")


def test_a_limit_without_a_window() -> None:
    (limit,) = parse_ratelimit('"default";r=999;pk=:dHJpYWwxMjEzMjM=:')
    assert limit.window is None


def test_other_parameters_are_kept_as_extra() -> None:
    (limit,) = parse_ratelimit('"sliding";q=12;r=6;t=1;acme-tier="gold";flag;at=@0;d=0.5')
    assert dict(limit.extra) == {
        "q": 12,
        "acme-tier": "gold",
        "flag": True,
        "at": datetime(1970, 1, 1, tzinfo=timezone.utc),
        "d": 0.5,
    }


def test_several_field_lines_are_combined_in_order() -> None:
    lines = ['"a";r=1', '"b";r=2;t=3']
    assert [lim.policy for lim in parse_ratelimit(lines)] == ["a", "b"]
    assert [pol.name for pol in parse_ratelimit_policy(iter(['"x";q=1', '"y";q=2']))] == ["x", "y"]


def test_an_empty_ratelimit_field_has_no_limits() -> None:
    assert parse_ratelimit("") == []
    assert parse_ratelimit([]) == []


def test_a_repeated_parameter_keeps_the_last_value() -> None:
    (limit,) = parse_ratelimit('"a";r=5;r=0')
    assert limit.remaining == 0


@pytest.mark.parametrize(
    "value",
    [
        "",
        "default;q=100",
        '"a";w=10',
        '"a";q=-1',
        '"a";q=1.0',
        '"a";q=?1',
        '"a";q="10"',
        '"a";q=1;w=0',
        '"a";q=1;w=-5',
        '"a";q=1;w=1.5',
        '"a";q=1;qu=requests',
        '"a";q=1;qu=1',
        '"a";q=1;pk="key"',
        '("a" "b");q=1',
        '"a";q=1,',
        '"a";q=1 "b";q=2',
        '"a";q=1000000000000000',
        '"café";q=1',
        '%"a";q=1',
        '"a";q=1;qu=%"requests"',
        '"a";q=1;qu=:cmVxdWVzdHM=:',
        "a;q=1",
        "1;q=1",
    ],
)
def test_malformed_policy_fields_raise(value: str) -> None:
    with pytest.raises(RateLimitError):
        parse_ratelimit_policy(value)


@pytest.mark.parametrize(
    "value",
    [
        "default;r=1",
        '"a";t=10',
        '"a";r=-1',
        '"a";r=1.5',
        '"a";r=?0',
        '"a";r=1;t=-1',
        '"a";r=1;t=2.5',
        '"a";r=1;t="10"',
        '"a";r=1;pk=abc',
        '"a";r=1;at=@999999999999999',
        '"a";r=1,,"b";r=2',
        '%"a";r=1',
        "?1;r=1",
        "@0;r=1",
        ":YQ==:;r=1",
        '"a";r=1;pk=%"key"',
        '"a";r=1;pk',
    ],
)
def test_malformed_limit_fields_raise(value: str) -> None:
    with pytest.raises(RateLimitError):
        parse_ratelimit(value)


def test_one_bad_line_rejects_the_whole_field() -> None:
    with pytest.raises(RateLimitError):
        parse_ratelimit(['"a";r=1', '"b"'])


def test_a_zero_window_limit_is_allowed() -> None:
    (limit,) = parse_ratelimit('"a";r=0;t=0')
    assert limit.window == 0


@pytest.mark.parametrize("value", [None, b'"a";r=1', [b'"a";r=1'], 5])
def test_non_text_input_is_a_type_error(value: object) -> None:
    with pytest.raises(TypeError):
        parse_ratelimit(value)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_ratelimit_policy(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("parse", "value", "key"),
    [
        (parse_ratelimit, '"a";r=?0', "r"),
        (parse_ratelimit, '"a";r=1;t=?1', "t"),
        (parse_ratelimit_policy, '"a";q=?1', "q"),
        (parse_ratelimit_policy, '"a";q=1;w=?1', "w"),
    ],
)
def test_a_boolean_is_not_an_integer_parameter(
    parse: Callable[[str], object], value: str, key: str
) -> None:
    with pytest.raises(RateLimitError, match=f"item 'a': {key} must be an Integer$"):
        parse(value)

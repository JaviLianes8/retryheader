from __future__ import annotations

from datetime import datetime, timezone

import pytest

from retryheader import (
    QuotaPolicy,
    ServiceLimit,
    build_ratelimit,
    build_ratelimit_policy,
    parse_ratelimit,
    parse_ratelimit_policy,
)
from tests.fixtures_text import draft_fields


@pytest.mark.parametrize("value", draft_fields("RateLimit-Policy"))
def test_draft_policies_round_trip(value: str) -> None:
    policies = parse_ratelimit_policy(value)
    assert parse_ratelimit_policy(build_ratelimit_policy(policies)) == policies


@pytest.mark.parametrize("value", draft_fields("RateLimit"))
def test_draft_limits_round_trip(value: str) -> None:
    limits = parse_ratelimit(value)
    rebuilt = parse_ratelimit(build_ratelimit(limits))
    assert rebuilt == limits
    assert [dict(lim.extra) for lim in rebuilt] == [dict(lim.extra) for lim in limits]


def test_build_policy_text() -> None:
    policies = [
        QuotaPolicy("burst", 100, 60),
        QuotaPolicy("bytes", 65535, 10, unit="content-bytes", partition_key=b"App-999"),
    ]
    assert build_ratelimit_policy(policies) == (
        '"burst";q=100;w=60, "bytes";q=65535;qu="content-bytes";w=10;pk=:QXBwLTk5OQ==:'
    )


def test_build_limit_text_with_extra_parameters() -> None:
    limit = ServiceLimit(
        "default", 0, 5, extra={"acme": "x", "on": True, "at": datetime(1970, 1, 1, 0, 0, 2)}
    )
    assert build_ratelimit([limit]) == '"default";r=0;t=5;acme="x";on;at=@2'


def test_no_limits_build_an_empty_value() -> None:
    assert build_ratelimit([]) == ""


def test_a_policy_field_needs_a_policy() -> None:
    with pytest.raises(ValueError):
        build_ratelimit_policy([])


@pytest.mark.parametrize(
    "extra",
    [
        {"q": 1},
        {"Bad": 1},
        {"x": float("nan")},
        {"x": 10**15},
        {"x": "café"},
        {"x": datetime(2026, 1, 1, 0, 0, 0, 1, tzinfo=timezone.utc)},
    ],
)
def test_unrepresentable_extra_parameters_are_rejected(extra: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        build_ratelimit_policy([QuotaPolicy("a", 1, extra=extra)])  # type: ignore[arg-type]


def test_unrepresentable_names_are_rejected() -> None:
    with pytest.raises(ValueError):
        build_ratelimit([ServiceLimit("tab\there", 1)])
    with pytest.raises(ValueError):
        build_ratelimit([ServiceLimit("big", 10**15)])


def test_items_of_the_wrong_class_are_rejected() -> None:
    with pytest.raises(TypeError):
        build_ratelimit([QuotaPolicy("a", 1)])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        build_ratelimit_policy([ServiceLimit("a", 1)])  # type: ignore[list-item]


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"quota": -1}, ValueError),
        ({"quota": True}, TypeError),
        ({"quota": 1.0}, TypeError),
        ({"window": 0}, ValueError),
        ({"window": "60"}, TypeError),
        ({"unit": None}, TypeError),
        ({"partition_key": "key"}, TypeError),
        ({"name": 5}, TypeError),
        ({"extra": [("a", 1)]}, TypeError),
    ],
)
def test_quota_policy_validates_its_fields(kwargs: dict[str, object], error: type) -> None:
    fields: dict[str, object] = {"name": "a", "quota": 1, **kwargs}
    with pytest.raises(error):
        QuotaPolicy(**fields)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"remaining": -1}, ValueError),
        ({"remaining": False}, TypeError),
        ({"window": -1}, ValueError),
        ({"window": 1.5}, TypeError),
        ({"policy": None}, TypeError),
    ],
)
def test_service_limit_validates_its_fields(kwargs: dict[str, object], error: type) -> None:
    fields: dict[str, object] = {"policy": "a", "remaining": 1, **kwargs}
    with pytest.raises(error):
        ServiceLimit(**fields)  # type: ignore[arg-type]


def test_instances_are_frozen_hashable_and_own_their_extra() -> None:
    extra = {"acme": 1}
    limit = ServiceLimit("a", 1, extra=extra)
    extra["acme"] = 2
    assert limit.extra["acme"] == 1
    with pytest.raises(TypeError):
        limit.extra["acme"] = 3  # type: ignore[index]
    with pytest.raises(AttributeError):
        limit.remaining = 5  # type: ignore[misc]
    assert hash(limit) == hash(ServiceLimit("a", 1))
    assert len({QuotaPolicy("a", 1), QuotaPolicy("a", 1)}) == 1

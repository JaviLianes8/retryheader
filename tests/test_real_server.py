"""Headers sent by a real rate limiting server: express-rate-limit 8.7.1 on Node.js 24.18.0.

Program output, not hand-written: scripts/capture_express_rate_limit.js runs the library
behind a real HTTP server and fetches it until it answers 429. These values were captured
on 2026-10-19. Its `draft-8` mode writes the RateLimit fields that draft -11 still defines;
its `draft-7` and `draft-6` modes write older shapes that draft -11 no longer reads.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from retryheader import (
    QuotaPolicy,
    RateLimitError,
    ServiceLimit,
    delay_from_headers,
    parse_ratelimit,
    parse_ratelimit_policy,
)

PK = ":MTJjYTE3YjQ5YWYy:"
# (status, headers) as the server sent them, in order.
DRAFT_8 = [
    (
        200,
        {
            "ratelimit": '"3-in-1min"; r=2; t=60',
            "ratelimit-policy": f'"3-in-1min"; q=3; w=60; pk={PK}',
        },
    ),
    (
        200,
        {
            "ratelimit": '"3-in-1min"; r=1; t=60',
            "ratelimit-policy": f'"3-in-1min"; q=3; w=60; pk={PK}',
        },
    ),
    (
        200,
        {
            "ratelimit": '"3-in-1min"; r=0; t=60',
            "ratelimit-policy": f'"3-in-1min"; q=3; w=60; pk={PK}',
        },
    ),
    (
        429,
        {
            "ratelimit": '"3-in-1min"; r=0; t=60',
            "ratelimit-policy": f'"3-in-1min"; q=3; w=60; pk={PK}',
            "retry-after": "60",
        },
    ),
]
HOURLY_429 = {
    "ratelimit": '"hourly"; r=0; t=3600',
    "ratelimit-policy": f'"hourly"; q=2; w=3600; pk={PK}',
    "retry-after": "3600",
}
DRAFT_7_429 = {
    "ratelimit": "limit=2, remaining=0, reset=60",
    "ratelimit-policy": "2;w=60",
    "retry-after": "60",
}
DRAFT_6_429 = {
    "ratelimit-limit": "2",
    "ratelimit-policy": "2;w=60",
    "ratelimit-remaining": "0",
    "ratelimit-reset": "60",
    "retry-after": "60",
}


@pytest.mark.parametrize(("index", "remaining"), [(0, 2), (1, 1), (2, 0), (3, 0)])
def test_draft_8_ratelimit_is_read_exactly(index: int, remaining: int) -> None:
    headers = DRAFT_8[index][1]
    assert parse_ratelimit(headers["ratelimit"]) == [ServiceLimit("3-in-1min", remaining, 60)]


def test_draft_8_policy_is_read_with_its_partition_key() -> None:
    (policy,) = parse_ratelimit_policy(DRAFT_8[0][1]["ratelimit-policy"])
    assert policy == QuotaPolicy("3-in-1min", 3, 60, partition_key=b"12ca17b49af2")
    assert policy.unit == "requests" and policy.extra == {}


def test_delay_follows_the_server_through_the_window() -> None:
    delays = [delay_from_headers(headers) for _, headers in DRAFT_8]
    # Quota left: no wait. Quota spent: the window, from RateLimit before the 429 and from
    # Retry-After with it.
    assert delays == [None, None, 60.0, 60.0]
    assert [status for status, _ in DRAFT_8] == [200, 200, 200, 429]


def test_delay_without_retry_after_comes_from_ratelimit() -> None:
    headers = {k: v for k, v in HOURLY_429.items() if k != "retry-after"}
    assert delay_from_headers(headers) == 3600.0
    assert delay_from_headers(HOURLY_429) == 3600.0


@pytest.mark.parametrize("headers", [DRAFT_7_429, DRAFT_6_429], ids=["draft-7", "draft-6"])
def test_older_shapes_fall_back_to_retry_after(headers: dict[str, str]) -> None:
    assert delay_from_headers(headers) == 60.0
    without = {k: v for k, v in headers.items() if k != "retry-after"}
    assert delay_from_headers(without) is None


@pytest.mark.parametrize(
    ("parse", "text"),
    [
        (parse_ratelimit, DRAFT_7_429["ratelimit"]),
        (parse_ratelimit_policy, DRAFT_7_429["ratelimit-policy"]),
    ],
)
def test_older_shapes_are_refused_by_the_parsers(parse: Callable[[str], object], text: str) -> None:
    with pytest.raises(RateLimitError):
        parse(text)

"""Seeded fuzzing: only the documented errors, short messages, and stable round trips."""

from __future__ import annotations

import contextlib
import math
import random
from datetime import datetime, timedelta, timezone

import pytest

from retryheader import (
    RateLimitError,
    RetryAfterError,
    build_ratelimit,
    build_ratelimit_policy,
    delay_from_headers,
    format_http_date,
    parse_http_date,
    parse_ratelimit,
    parse_ratelimit_policy,
    parse_retry_after,
)
from tests.generators import http_date, mutate, now, retry_after, sf_field

SEEDS = [101, 202, 303]


@pytest.mark.parametrize("seed", SEEDS)
def test_retry_after_only_raises_its_own_error_and_never_goes_negative(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(15000):
        value, reference = retry_after(rng), now(rng)
        try:
            delay = parse_retry_after(value, now=reference)
        except RetryAfterError as error:
            assert len(str(error)) <= 120, value
            with pytest.raises(RetryAfterError):
                parse_retry_after(value, now=reference, strict=True)
            continue
        assert delay >= 0 and not math.isnan(delay), value
        try:
            strict = parse_retry_after(value, now=reference, strict=True)
        except RetryAfterError:
            continue
        assert strict == delay, value


@pytest.mark.parametrize("seed", SEEDS)
def test_http_dates_are_aware_utc_and_strict_is_a_subset(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(15000):
        value = mutate(rng, http_date(rng), edits=rng.choice([0, 0, 1, 2]))
        reference = now(rng)
        try:
            moment = parse_http_date(value, now=reference)
        except RetryAfterError as error:
            assert len(str(error)) <= 120, value
            continue
        assert moment.utcoffset() == timedelta(0) and moment.tzinfo is timezone.utc, value
        assert parse_http_date(format_http_date(moment), strict=True) == moment
        with contextlib.suppress(RetryAfterError):
            assert parse_http_date(value, now=reference, strict=True) == moment, value


@pytest.mark.parametrize("seed", SEEDS)
def test_formatting_any_datetime_never_lands_earlier(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(5000):
        offset = timezone(timedelta(minutes=rng.randrange(-1439, 1440)))
        moment = datetime(2000, 1, 1, tzinfo=offset) + timedelta(
            microseconds=rng.randrange(-(10**16), 10**16)
        )
        written = parse_http_date(format_http_date(moment), strict=True)
        assert timedelta(0) <= written - moment < timedelta(seconds=1)


@pytest.mark.parametrize("seed", SEEDS)
def test_ratelimit_fields_round_trip_or_fail_whole(seed: int) -> None:
    rng = random.Random(seed)
    parsed = 0
    for _ in range(15000):
        field = sf_field(rng)
        for parse, build in (
            (parse_ratelimit, build_ratelimit),
            (parse_ratelimit_policy, build_ratelimit_policy),
        ):
            try:
                values = parse(field)
            except RateLimitError as error:
                assert len(str(error)) <= 200, field
                continue
            parsed += 1
            assert parse(build(values)) == values, field  # type: ignore[arg-type]
    assert parsed > 2000


@pytest.mark.parametrize("seed", SEEDS)
def test_delay_from_headers_never_raises_for_text_headers(seed: int) -> None:
    rng = random.Random(seed)
    names = ["Retry-After", "retry-after", "RateLimit", "RATELIMIT", "Date", "Age", "X"]
    for _ in range(10000):
        headers = [
            (rng.choice(names), rng.choice([retry_after(rng), sf_field(rng), http_date(rng)]))
            for _ in range(rng.randrange(5))
        ]
        delay = delay_from_headers(headers, now=now(rng), use_date_header=rng.random() < 0.5)
        assert delay is None or delay >= 0, headers

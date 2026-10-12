from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from retryheader import build_retry_after


def test_build_from_integer_seconds() -> None:
    assert build_retry_after(120) == "120"


@pytest.mark.parametrize(("value", "expected"), [(2.1, "3"), (2.5, "3"), (2.0, "2"), (0.001, "1")])
def test_a_fraction_rounds_up_so_the_client_never_returns_early(
    value: float, expected: str
) -> None:
    assert build_retry_after(value) == expected


def test_negative_values_clamp_to_zero() -> None:
    assert build_retry_after(-5) == "0"
    assert build_retry_after(-0.5) == "0"


def test_a_huge_integer_is_written_exactly() -> None:
    assert build_retry_after(10**20) == "100000000000000000000"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_are_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        build_retry_after(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (timedelta(minutes=2), "120"),
        (timedelta(seconds=1, microseconds=1), "2"),
        (timedelta(seconds=-1.5), "0"),
        (timedelta(seconds=-0.5), "0"),
        (timedelta(days=10**6, microseconds=1), str(86400 * 10**6 + 1)),
    ],
)
def test_build_from_a_timedelta(value: timedelta, expected: str) -> None:
    assert build_retry_after(value) == expected


def test_build_from_utc_datetime() -> None:
    when = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
    assert build_retry_after(when) == "Wed, 21 Oct 2026 07:28:00 GMT"


def test_build_from_naive_datetime_is_read_as_utc() -> None:
    assert build_retry_after(datetime(2026, 10, 21, 7, 28, 0)) == "Wed, 21 Oct 2026 07:28:00 GMT"


def test_build_from_a_datetime_with_microseconds_rounds_up() -> None:
    when = datetime(2026, 10, 21, 7, 28, 0, 500, tzinfo=timezone.utc)
    assert build_retry_after(when) == "Wed, 21 Oct 2026 07:28:01 GMT"


def test_build_rejects_booleans() -> None:
    with pytest.raises(TypeError):
        build_retry_after(True)


def test_build_rejects_unsupported_types() -> None:
    with pytest.raises(TypeError):
        build_retry_after("120")  # type: ignore[arg-type]

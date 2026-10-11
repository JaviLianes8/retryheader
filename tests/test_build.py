from datetime import datetime, timezone

import pytest

from retryheader import build_retry_after


def test_build_from_integer_seconds() -> None:
    assert build_retry_after(120) == "120"


def test_build_from_float_rounds_to_whole_seconds() -> None:
    assert build_retry_after(2.6) == "3"


def test_build_from_negative_clamps_to_zero() -> None:
    assert build_retry_after(-5) == "0"


def test_build_from_utc_datetime() -> None:
    when = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
    assert build_retry_after(when) == "Wed, 21 Oct 2026 07:28:00 GMT"


def test_build_from_naive_datetime_is_read_as_utc() -> None:
    when = datetime(2026, 10, 21, 7, 28, 0)
    assert build_retry_after(when) == "Wed, 21 Oct 2026 07:28:00 GMT"


def test_build_rejects_booleans() -> None:
    with pytest.raises(TypeError):
        build_retry_after(True)


def test_build_rejects_unsupported_types() -> None:
    with pytest.raises(TypeError):
        build_retry_after("120")  # type: ignore[arg-type]

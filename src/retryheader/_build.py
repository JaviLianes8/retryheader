"""Build a Retry-After header value from seconds, a timedelta or a datetime."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from ._httpdate import format_http_date


def build_retry_after(value: int | float | timedelta | datetime) -> str:
    """Render a Retry-After header value.

    A number of seconds or a timedelta becomes delay-seconds. A fraction rounds up
    and a negative delay becomes zero, so a client told to wait is never asked to come
    back sooner than intended. A datetime becomes an IMF-fixdate in GMT (a naive one is
    read as UTC, a fraction of a second rounds up).

    Raises TypeError for any other type (``bool`` included) and ValueError for NaN or
    an infinite number.
    """
    if isinstance(value, datetime):
        return format_http_date(value)
    if isinstance(value, timedelta):
        # Integer arithmetic: total_seconds() is a float and loses microseconds on
        # long delays, which could round a delay down.
        whole = value.days * 86400 + value.seconds + (1 if value.microseconds else 0)
        return str(max(0, whole))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"unsupported Retry-After value: {value!r}")
    if isinstance(value, int):
        try:
            return str(max(0, value))
        except ValueError as exc:  # the interpreter's limit on int to str conversion
            raise ValueError("Retry-After delay has too many digits to write") from exc
    return _seconds(value)


def _seconds(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError(f"Retry-After delay must be finite, not {value!r}")
    return str(max(0, math.ceil(value)))

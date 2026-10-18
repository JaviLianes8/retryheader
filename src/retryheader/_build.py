"""Build a Retry-After header value from seconds, a timedelta or a datetime."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from ._errors import type_name
from ._httpdate import format_http_date


def build_retry_after(value: int | float | timedelta | datetime) -> str:
    """Render a Retry-After header value.

    A number of seconds or a timedelta becomes delay-seconds. A fraction rounds up
    and a negative delay becomes zero, so a client told to wait is never asked to come
    back sooner than intended. A datetime becomes an IMF-fixdate in GMT (a naive one is
    read as UTC, a fraction of a second rounds up).

    Raises TypeError for any other type (``bool`` included), ValueError for NaN, an
    infinite number, an integer too long to write in decimal (more than 4300 digits by
    default) or a datetime whose UTC moment falls outside years 1 to 9999.

    >>> from datetime import datetime, timedelta
    >>> from retryheader import build_retry_after
    >>> build_retry_after(120)
    '120'
    >>> build_retry_after(2.1)
    '3'
    >>> build_retry_after(timedelta(minutes=2))
    '120'
    >>> build_retry_after(-5)
    '0'
    >>> build_retry_after(datetime(2026, 10, 21, 7, 28))
    'Wed, 21 Oct 2026 07:28:00 GMT'
    """
    if isinstance(value, datetime):
        return format_http_date(value)
    if isinstance(value, timedelta):
        # Integer arithmetic: total_seconds() is a float and loses microseconds on
        # long delays, which could round a delay down.
        whole = value.days * 86400 + value.seconds + (1 if value.microseconds else 0)
        return str(max(0, whole))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"unsupported Retry-After value of type {type_name(value)}")
    if isinstance(value, int):
        # int.__index__ gives a plain int, so a subclass (an IntEnum) cannot change
        # how the number is written.
        try:
            return str(max(0, int.__index__(value)))
        except ValueError as exc:  # the interpreter's limit on int to str conversion
            raise ValueError("Retry-After delay has too many digits to write") from exc
    seconds = float.__float__(value)
    if not math.isfinite(seconds):
        raise ValueError(f"Retry-After delay must be finite, not {seconds!r}")
    return str(max(0, math.ceil(seconds)))

"""Build a Retry-After header value from seconds or a datetime."""

from __future__ import annotations

from datetime import datetime
from email.utils import format_datetime

from ._time import as_utc


def build_retry_after(value: int | float | datetime) -> str:
    """Render a Retry-After header value.

    A number becomes a delta-seconds count, rounded to a whole second and
    clamped to zero. A datetime becomes an RFC 7231 HTTP-date in GMT, with a
    naive datetime read as UTC. Raises TypeError for any other type.
    """
    if isinstance(value, datetime):
        return format_datetime(as_utc(value), usegmt=True)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"unsupported Retry-After value: {value!r}")
    return str(max(0, round(value)))

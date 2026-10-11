"""Parse the HTTP Retry-After header into a delay in seconds."""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from ._errors import RetryAfterError
from ._time import as_utc


def parse_retry_after(value: str, *, now: datetime | None = None) -> float:
    """Return the delay in seconds for a Retry-After value, never negative.

    Accepts both forms from RFC 7231: a delta-seconds count such as ``"120"``
    or an HTTP-date such as ``"Wed, 21 Oct 2026 07:28:00 GMT"``. A date is
    resolved against ``now`` (the current UTC time by default) and a date in
    the past clamps to zero. Raises RetryAfterError on anything else.
    """
    text = value.strip()
    if not text:
        raise RetryAfterError("empty Retry-After value")
    if text.isascii() and text.isdigit():
        return float(text)
    when = _parse_http_date(text)
    reference = as_utc(now) if now is not None else datetime.now(timezone.utc)
    return max(0.0, (when - reference).total_seconds())


def _parse_http_date(text: str) -> datetime:
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError) as exc:
        raise RetryAfterError(f"invalid Retry-After value: {text!r}") from exc
    return as_utc(parsed)

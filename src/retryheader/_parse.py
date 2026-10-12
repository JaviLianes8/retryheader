"""Parse the HTTP Retry-After header into a delay in seconds."""

from __future__ import annotations

from datetime import datetime, timezone

from ._errors import RetryAfterError
from ._httpdate import parse_http_date
from ._time import as_utc, check_datetime, strip_ows


def parse_retry_after(value: str, *, now: datetime | None = None, strict: bool = False) -> float:
    """Return the delay in seconds for a Retry-After value, never negative.

    Accepts both forms from RFC 9110 section 10.2.3: delay-seconds, a run of ASCII
    digits such as ``"120"``, or an HTTP-date such as ``"Fri, 31 Dec 1999 23:59:59 GMT"``
    in any of its three formats. A date is resolved against ``now`` (the current UTC
    time by default; a naive value is read as UTC) and a date in the past gives zero.
    Spaces and tabs around the value are ignored. ``strict`` limits dates to the
    RFC 9110 grammar, see ``parse_http_date``.

    Raises RetryAfterError on anything else, TypeError when value is not a str.
    """
    if not isinstance(value, str):
        raise TypeError(f"Retry-After value must be a str, not {type(value).__name__}")
    if now is not None:
        check_datetime(now)
    text = strip_ows(value)
    if not text:
        raise RetryAfterError("empty Retry-After value")
    if text.isascii() and text.isdigit():
        # float() of a digit string never raises: huge values become infinity.
        return float(text)
    try:
        when = parse_http_date(text, now=now, strict=strict)
    except RetryAfterError as exc:
        raise RetryAfterError(f"invalid Retry-After value: {value!r}") from exc
    reference = as_utc(now) if now is not None else datetime.now(timezone.utc)
    return max(0.0, (when - reference).total_seconds())

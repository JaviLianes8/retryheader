"""Parse the HTTP Retry-After header into a delay in seconds."""

from __future__ import annotations

from datetime import datetime, timezone

from ._errors import RetryAfterError, quote
from ._httpdate import parse_http_date
from ._time import check_now, check_text, strip_ows


def parse_retry_after(value: str, *, now: datetime | None = None, strict: bool = False) -> float:
    """Return the delay in seconds for a Retry-After value, never negative.

    Accepts both forms from RFC 9110 section 10.2.3: delay-seconds, a run of ASCII
    digits such as ``"120"``, or an HTTP-date such as ``"Fri, 31 Dec 1999 23:59:59 GMT"``
    in any of its three formats. A date is resolved against ``now`` (the current UTC
    time by default; a naive value is read as UTC) and a date in the past gives zero.
    Spaces and tabs around the value are ignored. The grammar puts no bound on
    delay-seconds, so a value too large for a float gives ``math.inf``: cap the result
    before handing it to ``time.sleep`` or ``timedelta``. ``strict`` limits dates to the
    RFC 9110 grammar, see ``parse_http_date``.

    Raises RetryAfterError on anything else, TypeError when ``value`` is not a str or
    ``now`` not a datetime, ValueError (not a RetryAfterError) when ``now`` is aware and
    its UTC moment falls outside years 1 to 9999, whatever the value.

    >>> from datetime import datetime, timezone
    >>> from retryheader import parse_retry_after
    >>> parse_retry_after("120")
    120.0
    >>> now = datetime(1999, 12, 31, 23, 57, 59, tzinfo=timezone.utc)
    >>> parse_retry_after("Fri, 31 Dec 1999 23:59:59 GMT", now=now)
    120.0
    >>> parse_retry_after("Fri, 31 Dec 1999 23:00:00 GMT", now=now)
    0.0
    >>> parse_retry_after("1.5")
    Traceback (most recent call last):
    ...
    retryheader.RetryAfterError: invalid Retry-After value: '1.5'
    """
    value = check_text(value, "Retry-After value")
    now = check_now(now)
    text = strip_ows(value)
    if not text:
        raise RetryAfterError("empty Retry-After value")
    if text.isascii() and text.isdigit():
        # float() of a digit string never raises: huge values become infinity.
        return float(text)
    try:
        when = parse_http_date(text, now=now, strict=strict)
    except RetryAfterError as exc:
        raise RetryAfterError(f"invalid Retry-After value: {quote(value)}") from exc
    reference = now if now is not None else datetime.now(timezone.utc)
    return max(0.0, (when - reference).total_seconds())

"""Turn the headers of a response into how long to wait before the next request."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Protocol

from ._errors import RateLimitError, RetryAfterError, type_name
from ._httpdate import parse_http_date
from ._parse import parse_retry_after
from ._ratelimit import parse_ratelimit
from ._time import check_datetime, strip_ows


class HeaderItems(Protocol):
    """Anything with ``items()`` over (name, value) pairs, like http.client.HTTPMessage."""

    def items(self) -> Iterable[tuple[str, str]]: ...


Headers = Mapping[str, str] | HeaderItems | Iterable[tuple[str, str]]


def delay_from_headers(
    headers: Headers, *, now: datetime | None = None, use_date_header: bool = False
) -> float | None:
    """Return the seconds to wait before the next request, or None if nothing says to.

    ``headers`` is any mapping with ``items()`` (a dict, the headers of requests,
    httpx, aiohttp or http.client) or an iterable of (name, value) pairs; names match
    without regard to case and repeated fields are all read. Names and values must be str.

    A valid Retry-After wins, as the RateLimit draft requires; with several, the longest
    delay. Otherwise the longest effective window ``t`` of a RateLimit service limit
    whose available quota ``r`` is zero. Malformed fields are ignored, as both
    specifications ask, and so are the RateLimit fields of a response served from a cache
    (an ``Age`` above zero), as the draft recommends. An HTTP-date is measured from
    ``now`` (the current UTC time by default) or, with ``use_date_header``, from the
    response's own Date header when it is valid, which cancels any clock difference
    between client and server. Like ``parse_retry_after``, an absurdly large
    delay-seconds gives ``math.inf``. Raises TypeError when ``headers`` is not a mapping
    or an iterable of (name, value) pairs of str, or ``now`` is not a datetime.

    >>> from retryheader import delay_from_headers
    >>> delay_from_headers({"Retry-After": "120", "RateLimit": '"a";r=0;t=30'})
    120.0
    >>> delay_from_headers([("RateLimit", '"burst";r=0;t=30, "daily";r=9;t=86400')])
    30.0
    >>> delay_from_headers({"Retry-After": "soon", "Content-Type": "text/plain"}) is None
    True
    """
    if now is not None:
        check_datetime(now)
    fields = _collect(headers)
    reference = now
    if use_date_header:
        reference = _date(fields.get("date", []), now) or now
    delays = []
    for value in fields.get("retry-after", []):
        try:
            delays.append(parse_retry_after(value, now=reference))
        except RetryAfterError:
            continue
    if delays:
        return max(delays)
    if _from_cache(fields.get("age", [])):
        return None
    return _exhausted_window(fields.get("ratelimit", []))


def _collect(headers: Headers) -> dict[str, list[str]]:
    pairs = headers.items() if isinstance(headers, Mapping) else _items(headers)
    fields: dict[str, list[str]] = {}
    for pair in pairs:
        if isinstance(pair, (str, bytes, bytearray)):
            raise TypeError(f"each header must be a (name, value) pair, not {type_name(pair)}")
        try:
            name, value = pair
        except (TypeError, ValueError) as exc:
            raise TypeError("each header must be a (name, value) pair") from exc
        if not isinstance(name, str) or not isinstance(value, str):
            raise TypeError("header names and values must be str")
        fields.setdefault(str.__str__(name).lower(), []).append(str.__str__(value))
    return fields


def _items(headers: object) -> Iterable[tuple[str, str]]:
    # http.client.HTTPMessage and email.message.Message are not Mappings but have
    # items() that returns every field line, repeated ones included.
    items = getattr(headers, "items", None)
    if callable(items):
        pairs: Iterable[tuple[str, str]] = items()
        return pairs
    if isinstance(headers, (str, bytes, bytearray)) or not isinstance(headers, Iterable):
        raise TypeError("headers must be a mapping or an iterable of (name, value) pairs")
    return headers


def _date(values: list[str], now: datetime | None) -> datetime | None:
    if len(values) != 1:
        return None
    try:
        return parse_http_date(values[0], now=now)
    except RetryAfterError:
        return None


def _from_cache(values: list[str]) -> bool:
    # RFC 9111 section 5.1: Age is delta-seconds; a list keeps its first member and an
    # invalid value is ignored. A positive age means a cache served the response.
    if not values:
        return False
    first = strip_ows(",".join(values).split(",", 1)[0])
    return first.isascii() and first.isdigit() and first.strip("0") != ""


def _exhausted_window(lines: list[str]) -> float | None:
    if not lines:
        return None
    try:
        limits = parse_ratelimit(lines)
    except RateLimitError:
        return None
    windows = [lim.window for lim in limits if lim.remaining == 0 and lim.window is not None]
    return float(max(windows)) if windows else None

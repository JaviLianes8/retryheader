"""Parse and format HTTP-date values as RFC 9110 section 5.6.7 defines them."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from ._calendar import DAYS, MONTHS, assemble
from ._errors import RetryAfterError, quote
from ._lenient import parse_rfc5322
from ._time import as_utc, check_datetime, check_text, strip_ows

_DAYS = "|".join(DAYS)
_LONG_DAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
_MONTH = "|".join(MONTHS)
_TIME = r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
# The grammar is case sensitive and allows exactly one SP between fields, except the
# asctime day, which is padded with a second SP when it has one digit.
_FORMATS = (
    rf"(?P<dn>{_DAYS}), (?P<day>\d{{2}}) (?P<month>{_MONTH}) (?P<year>\d{{4}}) {_TIME} GMT",
    rf"(?P<dn>{_LONG_DAYS}), (?P<day>\d{{2}})-(?P<month>{_MONTH})-(?P<yy>\d{{2}}) {_TIME} GMT",
    rf"(?P<dn>{_DAYS}) (?P<month>{_MONTH}) (?P<day>\d{{2}}| \d) {_TIME} (?P<year>\d{{4}})",
)
_EXACT = tuple(re.compile(pattern, re.ASCII) for pattern in _FORMATS)
_ANY_CASE = tuple(re.compile(pattern, re.ASCII | re.IGNORECASE) for pattern in _FORMATS)


def parse_http_date(value: str, *, now: datetime | None = None, strict: bool = False) -> datetime:
    """Parse an HTTP-date into an aware UTC datetime.

    All three formats of RFC 9110 are accepted: IMF-fixdate
    (``Sun, 06 Nov 1994 08:49:37 GMT``), the obsolete RFC 850 form
    (``Sunday, 06-Nov-94 08:49:37 GMT``) and asctime (``Sun Nov  6 08:49:37 1994``).
    A two-digit year is placed within 50 years of ``now`` (the current UTC time by
    default), as the RFC requires, and a leap second ``:60`` reads as the next second.
    Surrounding spaces and tabs are ignored.

    ``strict=True`` accepts the RFC 9110 grammar and nothing else, and also requires the
    day name to be the day the date falls on. By default the parser is robust, as the RFC
    asks recipients to be: HTTP-dates in another letter case and RFC 5322 dates with an
    explicit zone (``+0200``, ``GMT``, ``UT``, ``UTC``, ``EST``) are accepted too, and the
    day name is not checked. A date without a zone, or with a zone whose offset is not
    known, is always rejected. Raises RetryAfterError on invalid input, TypeError when
    ``value`` is not a str or ``now`` not a datetime.

    >>> from datetime import datetime, timezone
    >>> from retryheader import parse_http_date
    >>> parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT")
    datetime.datetime(1994, 11, 6, 8, 49, 37, tzinfo=datetime.timezone.utc)
    >>> now = datetime(2026, 10, 21, tzinfo=timezone.utc)
    >>> parse_http_date("Monday, 01-Jan-60 00:00:00 GMT", now=now).year
    2060
    >>> parse_http_date("Sun, 06 Nov 1994 10:49:37 +0200").hour
    8
    >>> parse_http_date("Sun, 06 Nov 1994 10:49:37 +0200", strict=True)
    Traceback (most recent call last):
    ...
    retryheader.RetryAfterError: invalid HTTP-date: 'Sun, 06 Nov 1994 10:49:37 +0200'
    """
    value = check_text(value, "HTTP-date")
    if now is not None:
        check_datetime(now)
    text = strip_ows(value)
    for pattern in _EXACT:
        match = pattern.fullmatch(text)
        if match is not None:
            return _from_match(match, text, now, strict)
    if not strict:
        for pattern in _ANY_CASE:
            match = pattern.fullmatch(text)
            if match is not None:
                return _from_match(match, text, now, strict)
        lenient = parse_rfc5322(text, now)
        if lenient is not None:
            return lenient
    raise RetryAfterError(f"invalid HTTP-date: {quote(value)}")


def format_http_date(moment: datetime) -> str:
    """Render a datetime as an IMF-fixdate, the only form RFC 9110 lets senders use.

    A naive datetime is read as UTC. A fraction of a second rounds up to the next
    whole second, so the rendered moment is never earlier than the one given.
    Raises TypeError for a non-datetime, ValueError when the UTC moment (rounded up)
    falls outside years 1 to 9999.

    >>> from datetime import datetime, timedelta, timezone
    >>> from retryheader import format_http_date
    >>> format_http_date(datetime(1994, 11, 6, 8, 49, 37))
    'Sun, 06 Nov 1994 08:49:37 GMT'
    >>> format_http_date(datetime(1994, 11, 6, 10, 49, 36, 1, timezone(timedelta(hours=2))))
    'Sun, 06 Nov 1994 08:49:37 GMT'
    """
    check_datetime(moment)
    utc = as_utc(moment)
    if utc.microsecond:
        if utc.replace(microsecond=0) == datetime.max.replace(microsecond=0, tzinfo=utc.tzinfo):
            raise ValueError("rounding up passes the last representable second")
        utc = utc.replace(microsecond=0) + timedelta(seconds=1)
    day = DAYS[utc.weekday()]
    month = MONTHS[utc.month - 1]
    return f"{day}, {utc.day:02d} {month} {utc.year:04d} {utc:%H:%M:%S} GMT"


def _from_match(match: re.Match[str], text: str, now: datetime | None, strict: bool) -> datetime:
    fields = match.groupdict()
    year = fields.get("year")
    return assemble(
        year=int(year) if year is not None else None,
        yy=int(fields["yy"]) if fields.get("yy") is not None else None,
        month=MONTHS.index(fields["month"].title()) + 1,
        day=int(fields["day"]),
        clock=(int(fields["hour"]), int(fields["minute"]), int(fields["second"])),
        offset=0,
        now=now,
        text=text,
        weekday=DAYS.index(fields["dn"][:3].title()) if strict else None,
    )

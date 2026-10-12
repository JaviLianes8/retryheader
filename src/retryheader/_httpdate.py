"""Parse and format HTTP-date values as RFC 9110 section 5.6.7 defines them."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from ._calendar import MONTHS, assemble
from ._errors import RetryAfterError
from ._lenient import parse_rfc5322
from ._time import as_utc, check_datetime, strip_ows

_DAYS = "Mon|Tue|Wed|Thu|Fri|Sat|Sun"
_LONG_DAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
_MONTH = "|".join(MONTHS)
_TIME = r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})"
# The grammar is case sensitive and allows exactly one SP between fields, except the
# asctime day, which is padded with a second SP when it has one digit.
_FORMATS = (
    rf"(?:{_DAYS}), (?P<day>\d{{2}}) (?P<month>{_MONTH}) (?P<year>\d{{4}}) {_TIME} GMT",
    rf"(?:{_LONG_DAYS}), (?P<day>\d{{2}})-(?P<month>{_MONTH})-(?P<yy>\d{{2}}) {_TIME} GMT",
    rf"(?:{_DAYS}) (?P<month>{_MONTH}) (?P<day>\d{{2}}| \d) {_TIME} (?P<year>\d{{4}})",
)
_PATTERNS = tuple(re.compile(pattern, re.ASCII) for pattern in _FORMATS)


def parse_http_date(value: str, *, now: datetime | None = None, strict: bool = False) -> datetime:
    """Parse an HTTP-date into an aware UTC datetime.

    All three formats of RFC 9110 are accepted: IMF-fixdate
    (``Sun, 06 Nov 1994 08:49:37 GMT``), the obsolete RFC 850 form
    (``Sunday, 06-Nov-94 08:49:37 GMT``) and asctime (``Sun Nov  6 08:49:37 1994``).
    A two-digit year is placed within 50 years of ``now`` (the current UTC time by
    default), as the RFC requires, and a leap second ``:60`` reads as the next second.
    Surrounding spaces and tabs are ignored.

    Unless ``strict`` is true, RFC 5322 dates with an explicit zone (``+0200``,
    ``GMT``, ``UTC``, ``EST``) and HTTP-dates in another letter case are accepted too,
    since the RFC asks recipients to be robust. A date without a zone is always
    rejected. Raises RetryAfterError on invalid input, TypeError on a non-string.
    """
    if not isinstance(value, str):
        raise TypeError(f"HTTP-date must be a str, not {type(value).__name__}")
    if now is not None:
        check_datetime(now)
    text = strip_ows(value)
    for pattern in _PATTERNS:
        match = pattern.fullmatch(text)
        if match is not None:
            return _from_match(match, text, now)
    if not strict:
        for pattern in _PATTERNS:
            match = re.fullmatch(pattern.pattern, text, re.ASCII | re.IGNORECASE)
            if match is not None:
                return _from_match(match, text, now)
        lenient = parse_rfc5322(text, now)
        if lenient is not None:
            return lenient
    raise RetryAfterError(f"invalid HTTP-date: {value!r}")


def format_http_date(moment: datetime) -> str:
    """Render a datetime as an IMF-fixdate, the only form RFC 9110 lets senders use.

    A naive datetime is read as UTC. A fraction of a second rounds up to the next
    whole second, so the rendered moment is never earlier than the one given.
    """
    check_datetime(moment)
    utc = as_utc(moment)
    if utc.microsecond:
        utc = utc.replace(microsecond=0) + timedelta(seconds=1)
    day = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[utc.weekday()]
    month = MONTHS[utc.month - 1]
    return f"{day}, {utc.day:02d} {month} {utc.year:04d} {utc:%H:%M:%S} GMT"


def _from_match(match: re.Match[str], text: str, now: datetime | None) -> datetime:
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
    )

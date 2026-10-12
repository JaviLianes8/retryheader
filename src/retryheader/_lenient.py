"""The robust fallback: RFC 5322 dates that carry an explicit zone."""

from __future__ import annotations

import re
from datetime import datetime

from ._calendar import MONTHS, assemble

# RFC 5322 section 3.3 date-time, with its obsolete forms (two-digit years, named US
# zones, optional seconds and flexible spacing). Military single-letter zones are left
# out on purpose: RFC 5322 says they carry no reliable meaning.
_DATE = re.compile(
    r"(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[ \t]*,[ \t]*)?"
    rf"(?P<day>\d{{1,2}})[ \t]+(?P<month>{'|'.join(MONTHS)})[ \t]+(?P<year>\d{{4}}|\d{{2}})"
    r"[ \t]+(?P<hour>\d{2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?"
    r"[ \t]+(?P<zone>[+-]\d{4}|UT|UTC|GMT|EST|EDT|CST|CDT|MST|MDT|PST|PDT)",
    re.ASCII | re.IGNORECASE,
)
_NAMED = {"UT": 0, "UTC": 0, "GMT": 0, "EST": -5, "EDT": -4, "CST": -6, "CDT": -5}
_NAMED.update({"MST": -7, "MDT": -6, "PST": -8, "PDT": -7})


def parse_rfc5322(text: str, now: datetime | None) -> datetime | None:
    """Return the UTC moment of an RFC 5322 date, or None if it is not one."""
    match = _DATE.fullmatch(text)
    if match is None:
        return None
    fields = match.groupdict()
    offset = _zone_minutes(fields["zone"].upper())
    if offset is None:
        return None
    year = fields["year"]
    return assemble(
        year=int(year) if len(year) == 4 else None,
        yy=int(year) if len(year) == 2 else None,
        month=MONTHS.index(fields["month"].title()) + 1,
        day=int(fields["day"]),
        clock=(int(fields["hour"]), int(fields["minute"]), int(fields["second"] or 0)),
        offset=offset,
        now=now,
        text=text,
    )


def _zone_minutes(zone: str) -> int | None:
    if zone in _NAMED:
        return _NAMED[zone] * 60
    hours, minutes = int(zone[1:3]), int(zone[3:5])
    if minutes > 59:
        return None
    sign = -1 if zone[0] == "-" else 1
    return sign * (hours * 60 + minutes)

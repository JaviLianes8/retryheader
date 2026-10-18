"""The robust fallback: RFC 5322 dates that carry an explicit zone."""

from __future__ import annotations

import re
from datetime import datetime

from ._calendar import DAYS, MONTHS, assemble

# RFC 5322 section 3.3 date-time, with its obsolete forms (two- and three-digit years,
# named US zones, optional seconds and flexible spacing) but without comments. Erratum
# 6639 (verified) makes the space before a named zone optional. Military single-letter
# zones and unknown names are left out on purpose: RFC 5322 says their meaning is
# unreliable, so the moment would be a guess. "UTC" is accepted as a synonym of "UT".
_DATE = re.compile(
    rf"(?:(?:{'|'.join(DAYS)})[ \t]*,[ \t]*)?"
    rf"(?P<day>\d{{1,2}})[ \t]+(?P<month>{'|'.join(MONTHS)})[ \t]+(?P<year>\d{{2,4}})"
    r"[ \t]+(?P<hour>\d{2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?"
    r"(?:[ \t]+(?P<offset>[+-]\d{4})|[ \t]*(?P<named>UT|UTC|GMT|EST|EDT|CST|CDT|MST|MDT|PST|PDT))",
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
    if fields["named"] is not None:
        offset = _NAMED[fields["named"].upper()] * 60
    else:
        zone = fields["offset"]
        hours, minutes = int(zone[1:3]), int(zone[3:5])
        # RFC 5322 section 3.3: the last two digits of the zone are within 00 to 59.
        if minutes > 59:
            return None
        offset = (-1 if zone[0] == "-" else 1) * (hours * 60 + minutes)
    # RFC 5322 section 4.3: a two-digit year below 50 is 20xx, from 50 it is 19xx, and
    # a three-digit year is counted from 1900.
    year = int(fields["year"])
    if len(fields["year"]) == 2:
        year += 2000 if year < 50 else 1900
    elif len(fields["year"]) == 3:
        year += 1900
    return assemble(
        year=year,
        yy=None,
        month=MONTHS.index(fields["month"].title()) + 1,
        day=int(fields["day"]),
        clock=(int(fields["hour"]), int(fields["minute"]), int(fields["second"] or 0)),
        offset=offset,
        now=now,
        text=text,
    )

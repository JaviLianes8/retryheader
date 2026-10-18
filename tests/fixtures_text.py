"""The examples of RFC 9110 and of the RateLimit draft.

Two sources: short vectors cited below with their URL (they always run), and every
example cut from the texts fetched into tests/upstream (those tests skip until
`python scripts/fetch_upstream.py` has run). A test checks that each cited vector is
present, unchanged, in the fetched text.
"""

from __future__ import annotations

import re

from tests.upstream_files import section, text

RFC9110 = "rfc9110.txt"
DRAFT = "draft-ietf-httpapi-ratelimit-headers-11.txt"
RFC9110_URL = "https://www.rfc-editor.org/rfc/rfc9110.txt"
DRAFT_URL = "https://www.ietf.org/archive/id/draft-ietf-httpapi-ratelimit-headers-11.txt"

# RFC 9110 section 10.2.3, the two Retry-After examples (RFC9110_URL).
CITED_RETRY_AFTER = ["Fri, 31 Dec 1999 23:59:59 GMT", "120"]
# RFC 9110 section 5.6.7, one moment in the three HTTP-date formats (RFC9110_URL).
CITED_DATES = [
    "Sun, 06 Nov 1994 08:49:37 GMT",
    "Sunday, 06-Nov-94 08:49:37 GMT",
    "Sun Nov  6 08:49:37 1994",
]
# Draft -11 sections 3, 3.2, 4 and 4.2 (DRAFT_URL).
CITED_POLICIES = [
    '"burst";q=100;w=60,"daily";q=1000;w=86400',
    '"peruser";q=65535;qu="content-bytes";w=10;pk=:sdfjLJUOUH==:',
]
CITED_LIMITS = ['"default";r=50;t=30', '"default";r=300000000;t=60;pk=:QXBwLTk5OQ==:']
# Draft -11 appendix B.1.4, the headers of the throttled response (DRAFT_URL).
CITED_B14 = [
    ("Content-Type", "application/problem+json"),
    ("Date", "Mon, 05 Aug 2019 09:27:00 GMT"),
    ("Retry-After", "Mon, 05 Aug 2019 09:27:05 GMT"),
    ("RateLimit", '"default";r=0;t=5'),
]


def rfc9110_retry_after() -> list[str]:
    """The Retry-After field values of RFC 9110 section 10.2.3."""
    body = section(text(RFC9110), "10.2.3.  Retry-After")
    return re.findall(r"^\s+Retry-After: (.+)$", body, flags=re.MULTILINE)


def rfc9110_dates() -> list[str]:
    """The three HTTP-date examples of RFC 9110 section 5.6.7, comments removed."""
    body = section(text(RFC9110), "5.6.7.  Date/Time Formats")
    labels = r"IMF-fixdate|obsolete RFC 850 format|ANSI C's asctime\(\) format"
    return re.findall(rf"^\s+(\S.*?)\s+; (?:{labels})$", body, flags=re.MULTILINE)


def draft_fields(field: str) -> list[str]:
    """Every value of one field in the examples of the draft, in document order.

    The value excludes the optional whitespace after the colon (RFC 9110 5.5); one
    example line has none.
    """
    pattern = rf"^\s*{re.escape(field)}:[ \t]*(\".*)$"
    return [value.rstrip() for value in re.findall(pattern, text(DRAFT), flags=re.MULTILINE)]


def draft_response(heading: str) -> list[tuple[str, str]]:
    """The header fields of the response shown in one example section of the draft."""
    body = section(text(DRAFT), heading)
    lines = body[body.index("HTTP/1.1 4") :].splitlines()[1:]
    fields = []
    for line in lines:
        match = re.match(r"^\s+([A-Za-z-]+): (.+)$", line)
        if match is None:
            break
        fields.append((match.group(1), match.group(2)))
    return fields

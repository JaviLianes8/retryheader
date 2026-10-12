# retryheader

Parse and build the HTTP `Retry-After` header in both of its forms, HTTP-dates in all
three of their formats, and the `RateLimit` and `RateLimit-Policy` fields. Zero
dependencies, fully typed.

## Install

```
pip install retryheader
```

## How long should I wait?

`delay_from_headers` takes the headers of any response (a dict, the headers of
requests, httpx, aiohttp or `http.client`, or a list of name and value pairs) and
returns the seconds to wait, or `None` when nothing asks you to wait.

```python
from retryheader import delay_from_headers

headers = {"Retry-After": "120", "Content-Type": "application/json"}
print(delay_from_headers(headers))  # 120.0

# No Retry-After: the effective window of an exhausted RateLimit quota.
headers = [("RateLimit", '"burst";r=0;t=30, "daily";r=900;t=86400')]
print(delay_from_headers(headers))  # 30.0

print(delay_from_headers({"RateLimit": '"burst";r=4;t=30'}))  # None
```

A valid `Retry-After` always wins, as the RateLimit specification requires. Malformed
fields are ignored, as both specifications ask. Server and client clocks rarely agree,
so `use_date_header=True` measures an HTTP-date from the response's own `Date` header:

```python
from datetime import datetime, timezone

from retryheader import delay_from_headers

headers = {
    "Date": "Mon, 05 Aug 2019 09:27:00 GMT",
    "Retry-After": "Mon, 05 Aug 2019 09:27:05 GMT",
}
skewed_clock = datetime(2019, 8, 5, 9, 26, 50, tzinfo=timezone.utc)
print(delay_from_headers(headers, now=skewed_clock))  # 15.0
print(delay_from_headers(headers, now=skewed_clock, use_date_header=True))  # 5.0
```

## Retry-After

```python
from datetime import datetime, timedelta, timezone

from retryheader import RetryAfterError, build_retry_after, parse_retry_after

now = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
print(parse_retry_after("120"))  # 120.0
print(parse_retry_after("Wed, 21 Oct 2026 07:30:00 GMT", now=now))  # 120.0
print(parse_retry_after("Wednesday, 21-Oct-26 07:30:00 GMT", now=now))  # 120.0
print(parse_retry_after("Wed Oct 21 07:30:00 2026", now=now))  # 120.0
print(parse_retry_after("Wed, 21 Oct 2026 07:00:00 GMT", now=now))  # 0.0, never negative

try:
    parse_retry_after("-5")
except RetryAfterError as error:
    print(error)  # invalid Retry-After value: '-5'

print(build_retry_after(2.1))  # 3: fractions round up, so clients never come back early
print(build_retry_after(timedelta(minutes=2)))  # 120
print(build_retry_after(now))  # Wed, 21 Oct 2026 07:28:00 GMT
```

`now` defaults to the current UTC time and a naive datetime is read as UTC. A
malformed value raises `RetryAfterError` (a `ValueError`), so a bad header never
slips through as a silent zero; anything but a `str` raises `TypeError`.

## HTTP-date

RFC 9110 requires recipients to accept three formats. `parse_http_date` does, with the
RFC's rule for two-digit years (a year more than 50 years ahead of `now` belongs to
the previous century) and leap seconds:

```python
from datetime import datetime, timezone

from retryheader import format_http_date, parse_http_date

now = datetime(2026, 10, 21, tzinfo=timezone.utc)
print(parse_http_date("Sunday, 06-Nov-94 08:49:37 GMT", now=now))  # 1994-11-06 08:49:37+00:00
print(parse_http_date("Monday, 01-Jan-60 00:00:00 GMT", now=now).year)  # 2060
print(parse_http_date("Thu, 31 Dec 2026 23:59:60 GMT"))  # 2027-01-01 00:00:00+00:00

# Robust by default: RFC 5322 dates with an explicit zone. strict=True refuses them.
print(parse_http_date("Sun, 06 Nov 1994 10:49:37 +0200"))  # 1994-11-06 08:49:37+00:00

print(format_http_date(datetime(1994, 11, 6, 8, 49, 37)))  # Sun, 06 Nov 1994 08:49:37 GMT
```

A date without a zone is always rejected: guessing one would silently shift the delay.

## RateLimit and RateLimit-Policy

Both fields are Structured Field lists (RFC 9651), as defined by
draft-ietf-httpapi-ratelimit-headers-11. They parse into frozen dataclasses and build
back into field values:

```python
from retryheader import (
    QuotaPolicy,
    RateLimitError,
    ServiceLimit,
    build_ratelimit,
    build_ratelimit_policy,
    parse_ratelimit,
    parse_ratelimit_policy,
)

for policy in parse_ratelimit_policy('"burst";q=100;w=60, "daily";q=1000;w=86400'):
    print(policy.name, policy.quota, policy.window, policy.unit)
# burst 100 60 requests
# daily 1000 86400 requests

# Several field lines of one response are combined in order.
limits = parse_ratelimit(['"burst";r=0;t=30', '"daily";r=900;t=86400;acme-tier="gold"'])
print(limits[0].remaining, limits[0].window)  # 0 30
print(dict(limits[1].extra))  # {'acme-tier': 'gold'}

try:
    parse_ratelimit('"burst";r=-1')
except RateLimitError as error:
    print("ignored:", error)

print(build_ratelimit_policy([QuotaPolicy("burst", 100, 60)]))  # "burst";q=100;w=60
print(build_ratelimit([ServiceLimit("burst", 0, 30, partition_key=b"user-1")]))
# "burst";r=0;t=30;pk=:dXNlci0x:
```

A malformed field raises `RateLimitError` as a whole, with no partial result: the
specification says such a field MUST be ignored, and the error lets the caller do so.

## Why

RFC 9110 lets Retry-After carry a plain second count like `120` or an absolute
HTTP-date, and the date can arrive in any of three formats. Clients routinely handle
the first form, parse the date by hand, forget the timezone, misread two-digit years
or return a negative delay for a date already in the past. Servers that build the
header with ordinary rounding ask clients to come back early.

The closest package on PyPI, `retryafter`, is a retry decorator that pulls in FastAPI,
httpx and tenacity; it wraps calls rather than parsing the header. This library only
reads and writes the values, leans on nothing but the standard library, and is checked
against the examples of the specifications and the HTTP working group's structured
field test suite.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

# retryheader

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

A server that answers 429 or 503 tells the client how long to wait, in a `Retry-After`
header (seconds, or an HTTP-date in one of three formats) or in the newer `RateLimit`
fields. retryheader turns those headers into a number of seconds, and builds them for
servers, exactly as RFC 9110, RFC 9651 and the RateLimit draft define them. Zero
dependencies, fully typed.

## Install

```
pip install retryheader
```

## How long should I wait?

`delay_from_headers` takes the headers of any response (a dict, the headers of
requests, httpx, aiohttp, urllib3 or `http.client`, or a list of name and value pairs)
and returns the seconds to wait, or `None` when nothing asks you to wait.

```python
from retryheader import delay_from_headers

print(delay_from_headers({"Retry-After": "120", "Content-Type": "application/json"}))
# 120.0

# No Retry-After: the effective window of an exhausted RateLimit quota.
print(delay_from_headers([("RateLimit", '"burst";r=0;t=30, "daily";r=900;t=86400')]))
# 30.0
print(delay_from_headers({"RateLimit": '"burst";r=4;t=30'}))
# None
```

A valid `Retry-After` always wins, as the RateLimit draft requires. Malformed fields are
ignored, as both specifications ask. Server and client clocks rarely agree, so
`use_date_header=True` measures an HTTP-date from the response's own `Date` header:

```python
from datetime import datetime, timezone

from retryheader import delay_from_headers

headers = {
    "Date": "Mon, 05 Aug 2019 09:27:00 GMT",
    "Retry-After": "Mon, 05 Aug 2019 09:27:05 GMT",
}
skewed_clock = datetime(2019, 8, 5, 9, 26, 50, tzinfo=timezone.utc)
print(delay_from_headers(headers, now=skewed_clock))
# 15.0
print(delay_from_headers(headers, now=skewed_clock, use_date_header=True))
# 5.0
```

## Retry-After

```python
from datetime import datetime, timedelta, timezone

from retryheader import RetryAfterError, build_retry_after, parse_retry_after

now = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
print(parse_retry_after("120"), parse_retry_after("Wed, 21 Oct 2026 07:30:00 GMT", now=now))
# 120.0 120.0
print(parse_retry_after("Wednesday, 21-Oct-26 07:30:00 GMT", now=now))
# 120.0
print(parse_retry_after("Wed, 21 Oct 2026 07:00:00 GMT", now=now))
# 0.0
try:
    parse_retry_after("-5")
except RetryAfterError as error:
    print(error)
# invalid Retry-After value: '-5'

# Fractions round up, so a client is never asked to come back early.
print(build_retry_after(2.1), build_retry_after(timedelta(minutes=2)))
# 3 120
print(build_retry_after(now))
# Wed, 21 Oct 2026 07:28:00 GMT
```

A date in the past gives zero, never a negative delay. Delay-seconds has no upper bound
in the grammar, so a value too large for a float comes back as `math.inf`: cap it before
sleeping (`min(delay, 3600)`).

## HTTP-date

RFC 9110 requires recipients to accept three formats. `parse_http_date` does, with the
RFC's rule for two-digit years (a year more than 50 years ahead of `now` belongs to the
previous century) and leap seconds. By default it is robust, as the RFC recommends:
other letter cases and RFC 5322 dates with a known zone are read too. `strict=True`
accepts the RFC 9110 grammar and nothing else.

```python
from datetime import datetime, timezone

from retryheader import format_http_date, parse_http_date

now = datetime(2026, 10, 21, tzinfo=timezone.utc)
print(parse_http_date("Monday, 01-Jan-60 00:00:00 GMT", now=now).year)
# 2060
print(parse_http_date("Thu, 31 Dec 2026 23:59:60 GMT"))
# 2027-01-01 00:00:00+00:00
print(parse_http_date("Sun, 06 Nov 1994 10:49:37 +0200"))
# 1994-11-06 08:49:37+00:00
print(format_http_date(datetime(1994, 11, 6, 8, 49, 37)))
# Sun, 06 Nov 1994 08:49:37 GMT
```

A date without a zone, or with a zone whose offset is not known, is always rejected:
guessing would silently shift the delay.

## RateLimit and RateLimit-Policy

Both fields are Structured Field lists (RFC 9651) defined by the Internet-Draft
draft-ietf-httpapi-ratelimit-headers-11 (not yet an RFC). They parse into frozen
dataclasses and build back into field values:

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
print(limits[0].remaining, limits[0].window, dict(limits[1].extra))
# 0 30 {'acme-tier': 'gold'}

try:
    parse_ratelimit('"burst";r=-1')
except RateLimitError as error:
    print(error)
# malformed RateLimit item 'burst': remaining must be at least 0, not -1

print(build_ratelimit_policy([QuotaPolicy("burst", 100, 60)]))
# "burst";q=100;w=60
print(build_ratelimit([ServiceLimit("burst", 0, 30, partition_key=b"user-1")]))
# "burst";r=0;t=30;pk=:dXNlci0x:
```

A malformed field raises `RateLimitError` as a whole, with no partial result: the draft
says such a field MUST be ignored, and the error lets the caller do so.

## Why

Reading Retry-After by hand goes wrong in quiet ways: a date in one of the two older
formats is not recognised, a missing zone is taken as UTC, a two-digit year lands in the
wrong century, a date in the past becomes a negative sleep, and a server that rounds
`2.5` to `2` asks clients back early. What the closest tools do, checked on 2026-10-18:

- Python's `email.utils.parsedate_to_datetime` returns a naive datetime for a date
  without a zone and places two-digit years with a fixed pivot (69 is 1969, 68 is 2068)
  instead of RFC 9110's 50-year window. Built on `email.utils`, `werkzeug.http.parse_date`
  (3.1.9) and urllib3's `Retry.parse_retry_after` (2.8.0) read a missing or unknown zone
  as UTC, and `werkzeug.http.http_date` drops a fraction of a second.
- `ratelimit-headers` (0.1.0) reads the older draft-07 `RateLimit-Limit`,
  `RateLimit-Remaining` and `RateLimit-Reset` fields, not the `RateLimit` and
  `RateLimit-Policy` fields of draft -11; it takes `-5` as minus five seconds and `1.5`
  as one second, and skips dates in the two obsolete formats.
- `httpdate` (1.2.0) parses and formats HTTP-dates only; `retryafter` (0.2.0) is a retry
  decorator that depends on FastAPI, httpx, tenacity and uvicorn; `http-sf`, by one of
  the authors of RFC 9651, parses any structured field but knows nothing of RateLimit.

retryheader does this one job with the standard library only. It is tested against the
examples and grammar of RFC 9110 and of the draft as published, the HTTP working group's
structured field test suite, the headers express-rate-limit sends from a real server,
and, as independent oracles, `http-sf`, werkzeug, urllib3 and Python's `email.utils`
and `http.cookiejar`.

## Documentation

- [Guide](https://github.com/JaviLianes8/retryheader/blob/main/GUIDE.md): every rule,
  error and edge case, and how to upgrade from 0.2.
- [Changelog](https://github.com/JaviLianes8/retryheader/blob/main/CHANGELOG.md)

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/retryheader/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

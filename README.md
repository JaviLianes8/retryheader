# retryheader

Parse and build the HTTP Retry-After header, both delta-seconds and HTTP-date forms, zero dependencies and typed.

## Install

```
pip install retryheader
```

## Usage

```python
from datetime import datetime, timezone

from retryheader import build_retry_after, parse_retry_after

# Delta-seconds form.
parse_retry_after("120")  # 120.0

# HTTP-date form, resolved against a reference time.
now = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
parse_retry_after("Wed, 21 Oct 2026 07:30:00 GMT", now=now)  # 120.0

# A date already in the past clamps to zero, never negative.
parse_retry_after("Wed, 21 Oct 2026 07:00:00 GMT", now=now)  # 0.0

# Build the header from a number of seconds.
build_retry_after(120)  # "120"

# Or from a datetime, rendered as an RFC 7231 HTTP-date in GMT.
build_retry_after(now)  # "Wed, 21 Oct 2026 07:28:00 GMT"
```

A malformed value raises `RetryAfterError`, so a bad header never slips through as a
silent zero.

## Why

RFC 7231 lets Retry-After carry two different shapes: a plain second count like `120`,
or an absolute HTTP-date like `Wed, 21 Oct 2026 07:28:00 GMT`. Clients routinely handle
the first and mishandle the second, parsing the date by hand, forgetting the timezone, or
returning a negative delay for a date already in the past.

The closest package on PyPI, `retryafter`, is a retry decorator that pulls in FastAPI,
httpx and tenacity; it wraps calls rather than parsing the header. There is no small,
typed, dependency-free library that just reads and writes the Retry-After value itself.
This is that library: it leans only on the standard library (`email.utils` for dates),
handles both forms, and never hands back a negative delay.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/

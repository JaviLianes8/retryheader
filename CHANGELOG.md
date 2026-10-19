# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-19

The public API is now stable: the thirteen names in `retryheader.__all__`, their
signatures, defaults and error types follow Semantic Versioning from this release on.
The RateLimit fields follow draft-ietf-httpapi-ratelimit-headers-11, still an
Internet-Draft.

### Stable

- Retry-After: `parse_retry_after` and `build_retry_after`.
- HTTP-date: `parse_http_date` (strict RFC 9110 or robust) and `format_http_date`.
- RateLimit and RateLimit-Policy: `parse_ratelimit`, `parse_ratelimit_policy`,
  `build_ratelimit`, `build_ratelimit_policy` and the `ServiceLimit` and `QuotaPolicy`
  values.
- `delay_from_headers`: the seconds to wait from the headers of a response.
- Errors: `RetryAfterError` and `RateLimitError` (both `ValueError`) for invalid text,
  `ValueError` for a value that cannot be built, `TypeError` for arguments of the wrong
  type.

### Fixed

- `import retryheader` failed on Python 3.10 with `ValueError: mutable default ... for
  field extra`, although 0.2.1 declared support for 3.10.
- Error messages quote at most 40 characters of the input. 0.2.1 quoted the whole input
  (a 1 MB value gave a 1 MB message), an integer beyond Python's 4300-digit printing
  limit made the message itself raise a `ValueError` about digits, and a value whose
  `repr` failed raised that error instead of `TypeError`.
- `build_ratelimit` and `build_ratelimit_policy` raised `decimal.InvalidOperation` for a
  float `extra` value of about 1e16 or more, and the caller's `decimal` context
  (precision, traps) could change the result or raise. Such a value is now a
  `ValueError`, and a private context is used.
- Numbers are written as plain numbers: an `int` subclass with its own `__str__` (an
  `IntEnum` on Python 3.10) no longer turns into its name in `build_retry_after` or in an
  `extra` parameter.
- A `str` subclass is read as its characters: its own `strip`, `isdigit` or `__repr__` no
  longer change how a value is parsed or reported.
- A leap second anywhere but 23:59:60 UTC is reported as such (the message said
  "impossible date").

### Changed

- `parse_http_date` and `parse_retry_after` with `strict=True` refuse a day name that
  is not the day the date falls on: RFC 9110 gives the day name the meaning of RFC 5322,
  where it MUST be the day implied by the date. The default mode still ignores it.
- The default mode reads a named zone right after the time (`08:49:37GMT`), as the
  verified RFC 5322 erratum 6639 allows.
- A RateLimit or RateLimit-Policy field is malformed when its item value or `qu` is a
  Display String (the draft requires a String) or when it holds a byte sequence made only
  of padding (`:=:`), which is padding at the beginning.
- `delay_from_headers` ignores the RateLimit fields of a response with an `Age` above
  zero, which came from a cache, as the draft recommends (section 7.3). A header that is
  not a `(name, value)` pair is a `TypeError`; 0.2.1 raised `ValueError`, or read a
  two-character string as a name and a value.
- `QuotaPolicy` and `ServiceLimit` check `extra` on creation: names must be `str` and
  values `int`, `float`, `str`, `bytes`, `bool` or `datetime` (`TypeError`; 0.2.1 failed
  only when building). They store plain `str`, `int` and `bytes`, give each instance its
  own empty `extra`, and show and pickle as `retryheader.QuotaPolicy` and
  `retryheader.ServiceLimit`, like the two errors; pickles made by 0.2.1 still load.
- `TypeError` messages name the type of the value instead of quoting it.
- The package no longer exposes the stray name `annotations`.

### Added

- Runnable examples in every public docstring, run as doctests, and a GUIDE with every
  rule, error and the upgrade notes.
- Tests against the specifications fetched at test time: the RFC 9110 grammar converted
  from its ABNF and compared with the strict parser, RFC 5322 and erratum 6639, the
  requirements and examples of the RateLimit draft, and the structured field test suite
  (now with its large-value cases). Tests against independent implementations (`http-sf`
  by one of the authors of RFC 9651, werkzeug, urllib3, `email.utils`,
  `http.cookiejar`), against PyPI 0.2.1, on the header objects of real client libraries
  and on the headers express-rate-limit sends from a real server; seeded fuzz and hostile
  input tests; an end-to-end test of the built wheel with a real local HTTP exchange and
  the upgrade from PyPI 0.2.1.
- The sdist ships no third-party text: the specification excerpts it carried are gone,
  and the tests cut the examples from the fetched texts (a few short cited vectors always
  run).

## [0.2.1]

### Changed

- The httpwg structured field test suite is no longer committed. `tests/upstream/MANIFEST.json`
  pins its files (URL, commit, size, sha256, licence) and `scripts/fetch_upstream.py` fetches
  them; the full suite skips until then, and a short set of cited vectors always runs.
- The sdist ships only the sources, tests and docs.

## [0.2.0]

### Added

- `delay_from_headers`: the seconds to wait from a response's headers. Retry-After
  first, then the effective window of an exhausted RateLimit quota; malformed fields
  ignored; optional use of the response's `Date` header as the clock.
- `parse_ratelimit` and `parse_ratelimit_policy` with the `ServiceLimit` and
  `QuotaPolicy` dataclasses, and `build_ratelimit` and `build_ratelimit_policy`, for
  the fields of draft-ietf-httpapi-ratelimit-headers-11. Malformed fields raise
  `RateLimitError`.
- `parse_http_date` and `format_http_date`.
- `build_retry_after` accepts a `timedelta`.
- `strict` keyword on `parse_retry_after` and `parse_http_date`.

### Changed

- HTTP-dates follow RFC 9110: the RFC 850 two-digit year is placed within 50 years of
  `now` (`Monday, 01-Jan-60` is 2060 in 2026, not 1960), a leap second reads as the
  next second, and a date without a zone is rejected instead of being read as UTC.
  RFC 5322 dates with an explicit zone are still accepted unless `strict=True`, with
  the RFC 5322 rule for their two- and three-digit years. A leap second is only
  accepted at 23:59:60 UTC.
- `build_retry_after` rounds a fraction of a second up (2.5 gives 3, not 2), for
  numbers and datetimes alike, so a client is never asked to come back early. NaN and
  infinity raise `ValueError`.
- Only spaces and tabs around a Retry-After value are ignored, as RFC 9110 defines
  optional whitespace; a value that is not a `str` raises `TypeError`.

## [0.1.0]

- Parse the Retry-After header in both forms with `parse_retry_after`, resolving an
  HTTP-date against a reference time and never returning a negative delay.
- Build the Retry-After header from a number of seconds or a datetime with
  `build_retry_after`.
- Raise `RetryAfterError` on a malformed value.

# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

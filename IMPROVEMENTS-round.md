# retryheader improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] HTTP-date: the three RFC 9110 formats, two-digit years, leap seconds, strict mode
- [x] Retry-After parsing: exact field whitespace, typed rejection, spec fixtures
- [x] Retry-After building: never earlier than asked, timedelta, rejects NaN and infinity
- [x] Structured field parser, checked against the httpwg test suite
- [x] RateLimit and RateLimit-Policy: typed parse and build
- [x] `delay_from_headers`: one call from a response's headers to a delay
- [x] Contracts: oracles, typing, README examples, installed wheel e2e
- [x] Docs: README, CHANGELOG, docstrings, packaging metadata
- [x] Gates: ruff format, ruff check, mypy --strict, pytest
- [x] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` parses and builds Retry-After with `email.utils`. Reading it against the
specifications turned up these gaps:

- RFC 9110 says a recipient MUST accept all three HTTP-date formats. The asctime form
  works by accident, the RFC 850 form resolves two-digit years with the `email.utils`
  rule (below 50 is 20xx) instead of the RFC 9110 rule (more than 50 years in the
  future means the previous century), so `Monday, 01-Jan-60` lands in 1960, not 2060.
- A leap second (`23:59:60`, allowed by the grammar) is rejected.
- Dates without any zone (`Wed, 21 Oct 2026 07:28:00`) are silently read as UTC, and
  `None` raises an `AttributeError` instead of a clear `TypeError`.
- `build_retry_after(2.5)` returns `"2"`: banker's rounding asks the client to come back
  earlier than the server wanted. A datetime with microseconds is truncated the same way.
  `nan` and `inf` raise unrelated errors.
- There is no support at all for the RateLimit and RateLimit-Policy fields that servers
  now send next to Retry-After, and no single call that turns a response into a delay.

## Sources (fetched 2026-10-12)

- RFC 9110, sections 5.6.7 (HTTP-date) and 10.2.3 (Retry-After), 5.5 and 5.6.3 (field
  values and whitespace): https://www.rfc-editor.org/rfc/rfc9110.txt
- RFC 9651, Structured Field Values, section 4 (parsing and serialising):
  https://www.rfc-editor.org/rfc/rfc9651.txt
- RateLimit header fields, draft-ietf-httpapi-ratelimit-headers-11 (23 May 2026, the
  latest revision on the datatracker on the fetch date):
  https://www.ietf.org/archive/id/draft-ietf-httpapi-ratelimit-headers-11.txt
- Structured field test suite, commit `781ba38464b2ec4c547e1e14d007d4f5ace7457e`:
  https://github.com/httpwg/structured-field-tests

## Ranked improvements

1. **HTTP-date per RFC 9110.** A dedicated parser for IMF-fixdate, the RFC 850 form and
   asctime, with the 50-year rule for two-digit years resolved against `now`, leap
   seconds, and impossible dates rejected. A lenient default still accepts RFC 5322
   dates that carry an explicit zone (the RFC asks recipients to be robust); `strict=True`
   accepts the grammar and nothing else. Public `parse_http_date` and `format_http_date`.
2. **Retry-After parsing to the letter.** Only SP and HTAB are trimmed (the field's
   optional whitespace), delay-seconds is `1*DIGIT` and nothing else, non-string input
   raises `TypeError`, every example in RFC 9110 is a fixture.
3. **Retry-After building that never undershoots.** Fractions round up, so does a
   datetime with microseconds, `timedelta` is accepted, `nan` and infinity raise
   `ValueError`.
4. **Structured field parser.** RFC 9651 lists and items, checked against every list
   and item case in the httpwg test suite, vendored verbatim with its source commit.
5. **RateLimit and RateLimit-Policy.** Frozen dataclasses `ServiceLimit` and
   `QuotaPolicy`, parse functions that reject malformed fields as a whole (the draft
   says malformed fields MUST be ignored, so the caller gets one clear error), several
   field lines combined as RFC 9651 requires, builders that round-trip.
6. **`delay_from_headers`.** Case-insensitive lookup in any mapping or list of pairs,
   Retry-After first (the draft says it takes precedence), then the effective window of
   an exhausted RateLimit quota, malformed fields ignored, optional use of the response
   `Date` header as the clock to cancel client skew.
7. **Typed public API, proven.** A test runs mypy on a snippet and checks the inferred
   types and that wrong argument types are rejected.
8. **Docs with runnable examples.** Every Python block in the README runs in the test
   suite. Docstrings on every public name, CHANGELOG entry.
9. **Packaging.** Supported version classifiers, keywords, version agreement with the
   metadata, and an installed-wheel e2e test.

## Review fixes

- `delay_from_headers` is typed to accept anything with `items()`, so
  `http.client.HTTPMessage` and `email.message.Message` pass `mypy --strict`.
- `ServiceLimit` and `QuotaPolicy` pickle, copy and go through `dataclasses.asdict`;
  `extra` is a read-only dict instead of a mapping proxy.
- A delay-seconds too large for a float is documented as `math.inf`.
- Datetimes whose UTC moment (rounded up) leaves years 1 to 9999 raise `ValueError`,
  not `OverflowError`; so does a delay with more digits than Python will print.
- A leap second is only accepted at 23:59:60 UTC.
- Lenient RFC 5322 dates read two- and three-digit years with the RFC 5322 rule.
- The structured field suite compares values with their types, the draft fixture
  includes the one example line without a space after the colon, and the tests pass
  `mypy --strict` too (the gate now checks them).

## Out of scope

- A command line tool: a header value is read by code that is about to sleep, and a
  shell user can read `120` without help.
- The legacy `X-RateLimit-*` headers: their meaning differs per vendor (epoch seconds
  for some, a delay for others), so a generic parser would guess.
- Sleeping or retrying: callers already have a retry loop; this library tells it how
  long to wait.

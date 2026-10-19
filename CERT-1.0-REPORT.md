# retryheader 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to retryheader. PyPI has 0.2.1, which is
byte for byte the `main` branch at 37aa903 (the wheel's modules compared with the tree), so
every change listed here is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (37aa903, same code as PyPI 0.2.1)
- [x] Baseline gates on 0.2.1
- [x] Ground truth fetched live (item 7)
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, oracle, fuzz and hostile tests (items 6, 7, 9)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.1, every Python (items 8, 10, 13, 14)
- [x] Author mutation round (item 18)
- [x] Gates (item 15)
- [x] PR #4 and trace guard CLEAN
- [x] QA lenses round 1: every finding fixed (0f47628, 2d5f019), nothing disputed
- [ ] QA lenses re-verification (item 19) and independent review (item 16)

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: the 13 names of 0.2.1 with their signatures, parameter names and defaults kept and pinned, plus `Token` and `DisplayString` made public in QA round 1; every behaviour change in CHANGELOG and GUIDE |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: 54 doctest lines over 9 modules; every README and GUIDE example runs as a test and prints what its comments say |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, typing checked from a consumer (`tests/test_typing.py`) |
| 5 | Typed, documented, bounded errors | PASS: `RetryAfterError` and `RateLimitError` (both `ValueError`), `ValueError` for values that cannot be built, `TypeError` for wrong types; messages quote at most 40 characters and describe a huge integer by its size |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: RFC 9110, RFC 5322 with erratum 6639, RFC 9651, draft -11 and the httpwg suite fetched with a hash manifest; http-sf, werkzeug, urllib3, `email.utils`, `http.cookiejar`, real client header objects, express-rate-limit output, PyPI 0.2.1 |
| 8 | Real e2e from the wheel | PASS: installed wheel driven from an empty folder with `-I` and a real local HTTP exchange; upgrade in place from PyPI 0.2.1; no CLI to drive |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.14, 3.12.12, 3.13.11, 3.14.2, 3.14.2t |
| 11 | README and `twine check` | PASS: `twine check --strict` PASSED, absolute links tested |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-19 |
| 13 | pyproject 1.0.0, Production/Stable | PASS: 3.10 to 3.14, MIT, Homepage/Source/Issues/Changelog, keywords, `dependencies = []` |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR #4 from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: author 38 mutants, 36 killed at once, 2 survivors killed by contracts added in 7310f6d |
| 19 | Five independent QA lenses | round 1 findings fixed (see QA round 1), re-verification pending |

## Baseline on 0.2.1 (before any change)

Fresh clone of `release/1.0.0` at 37aa903 on the laptop, CPython 3.14.6: `ruff format
--check .`, `ruff check .` and `mypy --strict src tests` exit 0; `pytest` 2416 passed, 1
skipped (the installed-wheel test, which needs `RETRYHEADER_E2E=1`).

Defects found in 0.2.1 by reading and then reproducing, all fixed and in the CHANGELOG:

- `import retryheader` failed on Python 3.10 (`ValueError: mutable default ... for field
  extra`), although 0.2.1 declared support for 3.10.
- Error messages quoted the whole input (a 1 MB value gave a 1 MB message); an integer past
  the 4300-digit printing limit made the message itself raise; a value whose `repr` failed
  raised that error instead of `TypeError`.
- `build_ratelimit` raised `decimal.InvalidOperation` for a float `extra` of about 1e25 and
  the caller's `decimal` context could change the result.
- An `IntEnum` was written by its name on Python 3.10; a `str` subclass could change how a
  value was parsed through its own `strip` or `isdigit`.
- A leap second away from 23:59:60 UTC was reported as an impossible date.

## API review (item 1)

Kept: the thirteen public names of 0.2.1 (fifteen since QA round 1 added `Token` and
`DisplayString`) with their signatures, parameter names and
defaults, pinned by `tests/test_contract_api.py`. Changed, all in the CHANGELOG and the
GUIDE: `strict=True` checks the day name; the default mode reads a zone glued to the time
(erratum 6639); a Display String where the draft requires a String and a byte sequence of
padding alone make a RateLimit field malformed; `delay_from_headers` ignores RateLimit
fields of a cached response (`Age` above zero) and raises `TypeError` for a header that is
not a pair; `QuotaPolicy` and `ServiceLimit` check `extra` on creation, store plain values
and pickle as `retryheader.<Name>` (0.2.1 pickles still load); `TypeError` messages name
the type; the stray `annotations` name is gone.

## Ground truth (item 7)

Fetched by `scripts/fetch_upstream.py` into the ignored `tests/upstream` folder;
`tests/upstream/MANIFEST.json` records URL, revision, date, size, sha256 and licence, and
the tests check the hash before reading. Nothing fetched is committed or shipped. All 28
files were fetched again on 2026-10-19 and matched the manifest.

- RFC 9110 (https://www.rfc-editor.org/rfc/rfc9110.txt, 2026-10-18): the HTTP-date,
  delay-seconds and OWS rules are converted from the fetched ABNF (`tests/abnf.py`) and
  seeded candidates must be accepted by the strict parser exactly when the grammar and the
  calendar say so; the examples are cut from the text.
- RFC 5322 and verified erratum 6639 (rfc-editor.org, 2026-10-18): zones, years and the
  glued zone of the robust mode, read from the text.
- RFC 9651 and the httpwg structured-field-tests at commit 781ba38 (fetched 2026-10-13):
  every parse and serialisation case.
- draft-ietf-httpapi-ratelimit-headers-11 (ietf.org archive, 2026-10-18): each requirement
  the parsers rely on is located in the text and exercised, its example responses are cut
  from it.
- Independent implementations run live (`tests/test_oracles_libs.py`, `tests/test_oracle.py`):
  http-sf 1.4.0 (RFC 9651, by one of its authors) on 18,000 seeded lists and 6,000 seeded
  serialisations; werkzeug 3.1.9 and urllib3 2.8.0 on 3,000 dates and delays each;
  `email.utils` and `http.cookiejar` on seeded dates. On Python 3.10 only, http-sf accepts
  `:=:` because that version's `base64` decodes padding alone; the test allows exactly that.
- Real client header objects (`tests/test_clients.py`): requests 2.34.2, httpx 0.28.1,
  multidict 7.1.0 (aiohttp), urllib3, werkzeug, `http.client` and `email`.
- Real server output (`tests/test_real_server.py`): express-rate-limit 8.7.1 on Node.js
  24.18.0 behind a real HTTP server (`scripts/capture_express_rate_limit.js`), captured
  2026-10-19: its draft-8 fields read exactly; its draft-7 and draft-6 shapes are refused
  and `delay_from_headers` falls back to Retry-After, as the GUIDE says.
- PyPI 0.2.1 as an oracle (`tests/test_upgrade.py`, `RETRYHEADER_V021`): 27,000 calls give
  the same results and error families, except the documented changes.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`, three seeds each: 15,000 Retry-After values and 15,000 dates (only
the documented errors, messages of at most 120 characters, never a negative delay, strict
accepts a subset of the default mode), 5,000 datetimes formatted never earlier than given,
15,000 RateLimit fields that round trip or fail as a whole, 10,000 header sets that
`delay_from_headers` reads without raising. `tests/test_hostile.py`: time grows linearly
from 40,000 to 320,000 units over fifteen input shapes, messages stay under 200 characters
for 1 MB values, huge integers and huge type names, odd types are a clean `TypeError`.

## Author mutation round (item 18)

38 mutants over 14 modules, each applied alone to a copy of the tree on another machine,
the full suite (fetched sources, oracles and the 0.2.1 oracle present) run with `-x` and a
300 s per-test limit. 36 were killed at once. Two survived: M25 (a Boolean accepted where
an Integer parameter is required, caught later by the value types but with another message)
and M36 (inputs of 41 to 4,000 characters quoted in full). Contracts added in 7310f6d kill
both, checked against each mutant. The table is in
[CERT-1.0-MUTANTS.md](https://github.com/JaviLianes8/retryheader/blob/main/CERT-1.0-MUTANTS.md).

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- Wheel: the package, `py.typed`, LICENSE and metadata only; `Requires-Dist` only in the
  dev extra. sdist: source, tests with only the manifest of the fetched files, docs, the
  fetch script; no scratch files, no process notes. `twine check --strict` PASSED for both.
- Every interpreter on this PC from `requires-python` up, on another machine: the wheel
  installed in a fresh venv and the sdist's own suite run with `src` removed (fetched
  sources, oracles and the 0.2.1 oracle present). 3.8 and 3.9 are below
  `requires-python`; 3.13t is not installed here.

At cb676fa: CPython 3.10.19 2580 passed and 6 skipped (the three e2e tests, which need
the source tree and run separately, and the three 0.2.1 oracle tests, since 0.2.1 never
imported on 3.10); 3.11.14, 3.12.12, 3.13.11, 3.14.2 and 3.14.2 free-threaded 2583 passed
and 3 skipped each (the e2e tests). Each run imported the installed 1.0.0 from
`site-packages`.

## Gates (item 15)

At cb676fa on another machine from a fresh clone, CPython 3.14.2, each command on its own,
with the fetched sources, http-sf, werkzeug, urllib3, httpx, requests, multidict, the 0.2.1
oracle, `RETRYHEADER_E2E=1` and `RETRYHEADER_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (2586 passed,
no skips) all exit 0. The e2e tests built the wheel and sdist, inspected both, installed
the wheel in a fresh venv and drove it from an empty folder, and installed 0.2.1 from PyPI,
upgraded it in place and compared the answers and the pickles both ways.

## QA round 1 (item 19)

Lenses a (API and docs), b (correctness and ground truth), c (adversarial), d (packaging)
and e (contract strength) ran on 0ea7f97. Lens d reported no finding; lens b's evidence
entry needs no change. Every other finding is fixed; nothing is disputed. Each behaviour
fix first got a contract that failed on 0ea7f97 (`tests/test_contract_public_types.py`,
`tests/test_contract_inputs.py`), then the code was changed until it passed.

| Finding | Fix | Pinned by |
| --- | --- | --- |
| a-F1 `get_type_hints` and pydantic fail on `QuotaPolicy` and `ServiceLimit` | `_ratelimit_types.py` drops postponed annotations, so the annotations are real objects | `test_every_public_annotation_resolves` (all 15 names), `test_pydantic_can_validate_the_value_types` |
| a-F2 pickles name private modules; no public way to build a Token or a Display String | `QuotaPolicy` and `ServiceLimit` pickle through their constructor with `extra` as a plain dict; `Token` and `DisplayString` are public (`__all__` has 15 names) and show as `retryheader.<Name>`; the GUIDE spells out the unexported aliases | `test_pickles_of_public_values_name_no_private_module` (every protocol), `test_parsed_tokens_and_display_strings_are_the_public_types`, `test_tokens_and_display_strings_are_built_in_their_own_form` |
| a-F3 CHANGELOG says 1e16 | CHANGELOG and this report say about 1e25 (measured on 0.2.1: `ValueError` up to 1e24) | docs |
| a-F4 GUIDE wording on `Date` | GUIDE and docstring: exactly one `Date` field line, and it is valid (singleton field) | `test_the_date_header_counts_only_as_one_valid_field_line` |
| b-F1 empty first member of `Age` | the first non-empty member is read (RFC 9110 5.6.1.2) | `test_the_first_non_empty_age_member_is_read`, `test_an_empty_or_zero_age_keeps_the_ratelimit_fields` |
| b-F2 obsolete time with spaces around the colons | the robust mode reads `[ 	]*` around the time colons (RFC 5322 4.3 obs-hour, obs-minute, obs-second) | `test_the_obsolete_time_with_spaces_around_colons_is_read`; the 0.2.1 oracle allows for it |
| c-F1 aware `now` with no UTC moment raises a stray `ValueError` for some header forms only | `now` is checked and converted to UTC on entry of `parse_retry_after`, `parse_http_date` and `delay_from_headers`: one documented `ValueError` whatever the value | `test_a_now_without_a_utc_equivalent_is_one_value_error` (8 calls x both boundaries) |
| c-F2 `datetime` and `timedelta` subclasses control the output (CR/LF injection, `IndexError`) | values are copied through the base class descriptors before use | `test_datetime_and_timedelta_subclasses_are_read_as_their_values` |
| c-F3 `extra` keeps subclasses | every `extra` value is stored as its exact built-in type (`Token` and `DisplayString` keep theirs) | `test_extra_values_are_stored_as_plain_builtins` |
| c-F4 counts past 4300 digits break `repr` | counts and integer `extra` values past 15 digits are a `ValueError` on creation | `test_counts_past_fifteen_digits_are_refused_on_creation`, `test_windows_and_integer_extras_past_fifteen_digits_are_refused` |
| e-F1 M16 survives | contract for exactly 50 years ahead | `test_exactly_fifty_years_ahead_keeps_the_later_century` |
| e-F2 M45 survives | contract on the moment of `@N` and a non-zero round trip | `test_a_date_parameter_reads_as_its_moment_and_round_trips` |
| e-F3 M57 survives | contract for building `t=0` | `test_a_window_of_zero_is_written` |
| e-F4 M63 survives | contract that `:=:`, `:==:`, `:====:` are malformed | `test_a_byte_sequence_of_padding_alone_is_malformed` |
| e-F5 M71 survives | contract that a leading tab is malformed | `test_a_leading_tab_makes_the_field_malformed` |

Each of the five lens-e mutants, applied alone to the tree, now fails the new contracts
(M16, M45, M57, M63, M71: all killed). Every behaviour change is in the CHANGELOG 1.0.0
section and the GUIDE upgrade notes.

Gates at 2d5f019 on another machine from a fresh clone, CPython 3.14.2, with the fetched
sources, http-sf, werkzeug, urllib3, httpx, requests, multidict, pydantic, the 0.2.1
oracle, `RETRYHEADER_E2E=1` and `RETRYHEADER_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (2648 passed,
no skips) all exit 0. The new contracts also pass on CPython 3.10.19.

### Disputed findings

None.

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
- [x] QA lenses round 2 (a, e): every finding fixed (f26a4c8), nothing disputed
- [x] QA lenses round 3 (a, e): every finding fixed (7be512e), nothing disputed
- [x] QA lenses round 4 (e): every finding fixed (9640c0b), nothing disputed
- [x] QA lenses round 5 (e): every finding fixed (1fe199e), nothing disputed
- [x] Interpreter matrix run again at cc51284
- [x] QA lenses round 6 (b, c, e): every finding fixed (10eff2a), nothing disputed
- [x] QA round 7 (lens e re-check): every finding fixed (2694e2a), nothing disputed
- [x] QA round 8 (lens e re-check): every finding fixed (ba7138d), nothing disputed
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
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.14, 3.12.12, 3.13.11, 3.14.2, 3.14.2t, run again at cc51284 |
| 11 | README and `twine check` | PASS: `twine check --strict` PASSED, absolute links tested |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-19 |
| 13 | pyproject 1.0.0, Production/Stable | PASS: 3.10 to 3.14, MIT, Homepage/Source/Issues/Changelog, keywords, `dependencies = []` |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR #4 from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: author 38 mutants, 36 killed at once, 2 survivors killed by contracts added in 7310f6d |
| 19 | Five independent QA lenses | rounds 1 to 8 findings fixed; lens a PASS at f51bc1e (source, GUIDE and CHANGELOG changed in round 6); b, c, d and e re-verification pending |

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

Run again at cc51284, after the QA rounds, with pydantic added to the oracles: the wheel
and sdist built, `twine check --strict` PASSED for both, the contents as above. CPython
3.10.19 2659 passed and 6 skipped (the three e2e tests and the three 0.2.1 oracle tests);
3.11.14, 3.12.12, 3.13.11, 3.14.2 and 3.14.2 free-threaded 2662 passed and 3 skipped each
(the e2e tests, which the gates run). Each run imported the installed 1.0.0 from
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
| b-F2 obsolete time with spaces around the colons | the robust mode reads spaces and tabs around the time colons (RFC 5322 4.3 obs-hour, obs-minute, obs-second) | `test_the_obsolete_time_with_spaces_around_colons_is_read`; the 0.2.1 oracle allows for it |
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

## QA round 2 (item 19)

Lenses a and e re-ran on 6e152eb and each reported new findings; every one is fixed and
nothing is disputed.

| Finding | Fix | Pinned by |
| --- | --- | --- |
| a-N1 a `DisplayString` with a lone surrogate fails with the codec's `UnicodeEncodeError`, and its docstring says it may hold any text | building it raises the library's own `ValueError` ("display strings hold text UTF-8 can encode: ...", input quoted and cut to 40 characters); the docstring and GUIDE say it holds any text UTF-8 can encode; CHANGELOG and GUIDE upgrade notes record the change | `test_a_display_string_utf8_cannot_encode_is_the_librarys_value_error` (failed on 6e152eb, 3 cases) |
| e-N07 the fold of an ambiguous `now` is not pinned | contract with a fold-aware zone (hand-written model of America/New_York on 2026-11-01; tzdata is not installed on this PC): fold=0 reads EDT, fold=1 reads EST | `test_an_ambiguous_now_is_read_with_the_offset_its_fold_picks` |
| e-N12 a `now` whose tzinfo returns no offset is not pinned as UTC | contract that such a `now` gives the same delay as the naive value (UTC) | `test_a_now_whose_tzinfo_has_no_offset_is_read_as_utc_not_local_time` |
| e-N04 a `timedelta` subclass overriding `seconds` is not pinned | contract with a subclass whose `days`, `seconds` and `microseconds` all lie | `test_a_timedelta_subclass_is_read_through_the_base_descriptors` |
| e-N09 a `datetime` subclass overriding `tzinfo` is not pinned | contract with a subclass whose `tzinfo` and `fold` lie | `test_a_datetime_subclass_is_read_with_its_stored_tzinfo_and_fold` |

The time contracts live in `tests/test_contract_time.py`. Each reported mutant of
`_time.py`, applied alone, now fails them: `fold=0` (N07), `if moment.tzinfo is None:`
(N12, on a host in Europe/Madrid; the result of the mutant depends on the host's zone),
`delta.seconds` (N04), `moment.tzinfo` (N09), plus `delta.microseconds`, `delta.days`
and `fold=moment.fold`: all seven killed. The N1 contract failed on 6e152eb before the fix.

Gates at f26a4c8 on another machine from a fresh clone, CPython 3.14.2, with the fetched
sources, http-sf, werkzeug, urllib3, httpx, requests, multidict, pydantic, the 0.2.1
oracle, `RETRYHEADER_E2E=1` and `RETRYHEADER_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (2655 passed,
no skips) all exit 0.

### Disputed findings (round 2)

None.

## QA round 3 (item 19)

Lenses a and e re-ran on 5bb7461. Lens a confirmed N1 fixed and reported one docs
finding; lens e reported five contract gaps. Every one is fixed in 7be512e and nothing is
disputed. No behaviour changed in this round (tests and GUIDE only), so the CHANGELOG is
unchanged.

| Finding | Fix | Pinned by |
| --- | --- | --- |
| a-N2 the GUIDE reads as if creating a `DisplayString` with a lone surrogate raised | GUIDE: a `DisplayString` is checked when a field is built, not when it is created; `build_ratelimit` and `build_ratelimit_policy` raise the `ValueError`; the upgrade note says "when a field is built with it" (matches the docstring and the CHANGELOG) | docs |
| e-F1 the N12 contract bites only on a host not on UTC | the check also runs in a child process with `TZ=UTC-3` (honoured by POSIX and the Windows C runtime; the child asserts its local offset is 3 hours), so a UTC host catches the mutant too | `test_a_now_with_no_offset_ignores_the_host_time_zone_even_on_a_utc_host` |
| e-F2 a `now` with an offset but no `tzname` is not pinned as aware | contract with a tzinfo of +05:00 whose `dst` and `tzname` return None: the delay is 18060.0 | `test_a_now_with_an_offset_but_no_zone_name_is_read_with_its_offset` |
| e-F3 the descriptor reads of `plain_datetime` are not pinned | the `datetime` subclass contract now lies in every component (`year`, `month`, `day`, `hour`, `minute`, `second`, `microsecond`, `tzinfo`, `fold`) and checks both parsing and building | `test_a_datetime_subclass_is_read_with_its_stored_components` |
| e-F4 dropping `from None` survives | the contract asserts `__suppress_context__ is True` | `test_a_display_string_utf8_cannot_encode_is_the_librarys_value_error` |
| e-F5 replacing `quote(value)` with `value!r` survives | the contract adds a 10 001 character input and keeps the message under 120 characters | same test, case `after-10000` |

Each reported mutant, applied alone with `TZ=UTC0` (a host on UTC), now fails the new
contracts: `if moment.tzinfo is None:` (F1), `or moment.tzname() is None:` (F2),
`moment.year`, `moment.month`, `moment.day`, `moment.hour`, `moment.minute`,
`moment.second`, `moment.microsecond` in `plain_datetime` (F3), dropping `from None` (F4)
and `{value!r}` in `_display` (F5): all eleven killed.

Gates on 7be512e's tree on another machine from a fresh clone, CPython 3.14.2, `TZ=UTC0`,
with the fetched sources, http-sf, werkzeug, urllib3, httpx, requests, multidict,
pydantic, the 0.2.1 oracle, `RETRYHEADER_E2E=1` and `RETRYHEADER_E2E_PYPI=1`:
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests`
and `pytest` (2658 passed, no skips) all exit 0.

### Disputed findings (round 3)

None.

## QA round 4 (item 19)

Lens e re-ran on f51bc1e. It confirmed F1 to F5 killed under `TZ=UTC0` and under the
host zone, proved N16 (dropping `str.__str__` in `_display`) equivalent, and reported two
surviving mutants. Both are fixed in 9640c0b and nothing is disputed. No behaviour changed
in this round (tests only), so the CHANGELOG is unchanged.

| Finding | Fix | Pinned by |
| --- | --- | --- |
| e-N14 `from None` replaced with `from exc` in `_display` survives (`__suppress_context__` stays True, `__cause__` holds the codec error) | the contract also asserts `__cause__ is None` and that the formatted traceback has no `UnicodeEncodeError` | `test_a_display_string_utf8_cannot_encode_is_the_librarys_value_error` |
| e-N25 `isinstance(moment, date)` in `check_datetime` survives (a plain `date` fails later with CPython's descriptor message) | contract: `format_http_date(date(2026, 1, 1))` raises `TypeError` with exactly `expected a datetime, not date` | `test_format_rejects_a_plain_date_with_its_own_message` |

Each reported mutant, applied alone, now fails the new contract: `except UnicodeEncodeError
as exc: ... from exc` fails cases `after-60` and `after-10000`, and
`isinstance(moment, date)` fails the plain date contract.

Gates on 9640c0b's tree on another machine from a fresh clone, CPython 3.14, with the
fetched sources, http-sf, werkzeug, urllib3, httpx, requests, multidict, pydantic, the
0.2.1 oracle, `RETRYHEADER_E2E=1` and `RETRYHEADER_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (2659 tests)
all exit 0 in the host zone; the time, HTTP-date and public type contracts also pass with
`TZ=UTC0`.

### Disputed findings (round 4)

None.

## QA round 5 (item 19)

Lens e re-ran on 5111a36. It confirmed N14 and N25 killed under `TZ=UTC0` and under the
host zone, and reported four low findings: mutants that survive the suite. All four are
fixed in 1fe199e with new contracts, and nothing is disputed. No behaviour changed in this
round (tests only), so the CHANGELOG is unchanged.

| Finding | Fix | Pinned by |
| --- | --- | --- |
| e-N31 `isinstance(now, date)` in `check_now` survives (a plain `date` as `now` fails later with CPython's descriptor message) | contract: a `date` passed as `now` to `parse_retry_after`, `parse_http_date` and `delay_from_headers` raises `TypeError` with exactly `expected a datetime, not date` | `test_a_plain_date_as_now_is_refused_with_its_own_message` |
| e-N32 `name[: _LIMIT - 2]` and `len(name) < _LIMIT` in `type_name` survive (no test at the 40/41 character boundary) | contract: type names of 40, 41 and 200 characters give the exact message (40 shown whole, longer ones as 37 characters and `...`) | `test_a_type_name_in_a_message_is_cut_to_40_characters` |
| e-N33 dropping `str.__str__` in `_display` survives (reachable through a `ServiceLimit` subclass whose `extra` returns a `DisplayString` subclass with its own `encode`) | hostile subclass contract: the serialiser writes the real text, `m=%"ok"` | `test_a_display_string_subclass_is_written_as_its_real_text` |
| e-N36 the display string escapes (`%`, `"`, the SP and `~` range edges) were pinned only by the optional upstream corpus | hand-written contract from RFC 9651 section 4.1.11, no fetched files needed: `' "%~\x1f\x7f\u00e9'` is written as `%" %22%25~%1f%7f%c3%a9"` | `test_display_strings_escape_exactly_percent_quote_and_non_ascii` |

Each reported mutant, applied alone in a copy without the fetched files, now fails a new
contract: `isinstance(now, date)`, `name[: _LIMIT - 2]` (cases 41 and 200),
`len(name) < _LIMIT` (case 40), dropping `value = str.__str__(value)` in `_display`, and
`char in '%'`, `char in '"'`, `0x21 <= byte`, `byte <= 0x7D` in `_display`.

Gates on 1fe199e's tree on another machine from a fresh clone, CPython 3.14, with the
fetched sources, http-sf, werkzeug, urllib3, httpx, requests, multidict, pydantic, the
0.2.1 oracle, `RETRYHEADER_E2E=1` and `RETRYHEADER_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (2665 tests)
all exit 0 in the host zone; the time, HTTP-date, hostile input, RateLimit build,
serialiser and public type contracts (1112 tests) also pass with `TZ=UTC0`.

### Disputed findings (round 5)

None.

## Lens a re-check (item 19)

Lens a re-ran on f51bc1e: N2 confirmed fixed, about 30 new probes, every README and GUIDE
example executed on CPython 3.10, 3.13 and 3.14 with the outputs shown, no finding.
Verdict: PASS. Since then only tests and this report changed; no source, README, GUIDE or
CHANGELOG change.

## QA round 6 (item 19)

Lenses b, c and e ran on 1ee9bdd. Lens b re-derived every result from the fetched sources
and independent implementations (httpwg suite, 360k generated structured fields, 450k
HTTP-dates against its own RFC 9110 parser, 160k RFC 5322 dates, the builders against
`email.utils`, wsgiref and http-sf, 102 cases cut from the specifications, a real
express-rate-limit server) and reported one low finding. Lens c ran about 450 hostile
probes, 45 scaling shapes up to 1e6 and 1.8M seeded fuzz iterations with no failure and
reported three low findings. Lens e reported eight surviving mutants. All twelve are fixed
in 10eff2a, and nothing is disputed.

| Finding | Fix | Pinned by |
| --- | --- | --- |
| b-F1 a float `extra` rounds as its `repr`, not its binary value, unlike http-sf (`0.1235` gives `0.124`, http-sf `0.123`) | kept and documented, the alternative the finding offers: the httpwg serialisation tests (`serialisation-tests/number.json`, commit 781ba38) require `0.0025` to give `0.002` and `9.9995` to give `10.0`; rounding the binary value gives `0.003` and `9.999` (run here: http-sf 1.4.0 writes `0.003`, `-0.003` and `9.999`, so it fails three of those five vectors). The GUIDE and the `QuotaPolicy` docstring now state the rule, the vectors and the difference from http-sf | `test_a_float_rounds_as_its_repr_half_to_even` (`0.0025`, `-0.0025`, `0.0015`, `9.9995`, `0.1235`, `0.0005`, `-649356.5595`, `0.12351`) |
| c-C1 `extra` equality ignored the structured-field type (`k`, `k=1` and `k=1.0` equal, one entry in a set, three wire forms) | two `extra` mappings compare and hash by (name, exact type, value); a plain dict still compares by value. CHANGELOG (Changed) and GUIDE upgrade notes | `test_limits_differing_in_an_extra_type_are_not_equal`, `test_extra_hash_follows_the_type`, `test_limits_with_the_same_typed_extra_are_equal`, `test_extra_still_compares_with_a_plain_dict_by_value` |
| c-C2 `extra.__init__(...)` changed a frozen, hashed value in place | `__init__` refuses once the mapping is built (`TypeError: extra parameters are read only`). CHANGELOG (Fixed) | `test_extra_cannot_be_reinitialised`, `test_a_fresh_extra_mapping_still_builds` |
| c-C3 an `email.message.Message` with 8-bit bytes in any field made `delay_from_headers` raise `TypeError` (compat32 gives an `email.header.Header`) | such a value is read as its text; every other non-`str` value is still a `TypeError`. CHANGELOG (Fixed), GUIDE | `test_an_email_message_with_8bit_bytes_in_another_field_is_read`, `test_an_8bit_retry_after_in_an_email_message_is_ignored` |
| e-F1 (C10) `OverflowError` dropped from `assemble` survives | contract: a zone shift past year 1 or 9999 is `RetryAfterError`, and `None` from `delay_from_headers` | `test_a_zone_shift_past_the_calendar_is_a_retry_after_error` |
| e-F2 (H08) `re.IGNORECASE` dropped from the default mode survives | contract: RFC 850, asctime and IMF-fixdate in other letter cases read in the default mode | `test_the_default_mode_reads_any_letter_case` |
| e-F3 (H13) a short day name in the strict RFC 850 form survives | contract: strict mode rejects it, and the other letter cases | `test_strict_mode_rejects_a_short_rfc850_day_and_other_cases` |
| e-F4 (D12) `continue` to `break` on an invalid Retry-After line survives | contract: an invalid line before a valid one | `test_an_invalid_retry_after_line_never_hides_a_later_valid_one` |
| e-F5 (D17) truthiness instead of `is not None` on the window survives | contract: `r=0;t=0` gives `0.0` | `test_an_exhausted_limit_with_a_zero_window_waits_zero` |
| e-F6 (D11) the Date header resolved against the wall clock survives | contract: a two-digit Date year resolved against `now` in 2100 | `test_the_date_header_resolves_two_digit_years_against_now` |
| e-F7 (N07) the ASCII check of the structured field parser survives | contract: non-ASCII in a token, a key, a name, a string, at top level and a non-ASCII digit raise `RateLimitError`, and the field is ignored by `delay_from_headers` | `test_non_ascii_text_makes_a_ratelimit_field_malformed`, `test_a_malformed_non_ascii_ratelimit_field_is_ignored` |
| e-F8 (D15, Y14, Y17) the three type guards' messages were unpinned | contract: the exact messages, matched in full | `test_type_guards_say_what_is_wrong` |

The `extra` mapping and its value checks moved from `_ratelimit_types.py` to a new private
module `_extra.py` (the first would have passed 200 lines); no public name changed.

Each reported mutant, applied alone to a copy of the tree, fails the new contracts: C10,
H08, H13, D12, D17, D11, N07, D15, Y14 and Y17 as lens e described them, plus the three
fixes of this round reverted one at a time (C1, C2, C3). Before the fixes the new
contracts failed on 1ee9bdd for C1, C2 and C3 (18 failures) and passed for the rest.

Gates on 10eff2a's tree on another machine from a fresh clone, CPython 3.14, with the
fetched sources, http-sf, werkzeug, urllib3, httpx, requests, multidict, pydantic, the
0.2.1 oracle, `RETRYHEADER_E2E=1` and `RETRYHEADER_E2E_PYPI=1`: `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` and `pytest` (2720 passed)
all exit 0.

### Disputed findings (round 6)

None. b-F1 is fixed by documenting the rounding rule, the second fix the finding offers,
because changing it would break the httpwg serialisation vectors (evidence above).

## QA round 7 (item 19)

Lens e re-checked 436b63b with its own mutation round and reported three findings, all
gaps in the contracts on the `extra` mapping, none a behaviour bug. All three are fixed
in 2694e2a by a new contract file, `tests/test_contract_extra_mapping.py`, and nothing is
disputed. No behaviour changed, so the CHANGELOG is unchanged; the GUIDE now states the
dict-subclass equality and the pickling of `extra` that the new contracts pin.

| Finding | Fix | Pinned by |
| --- | --- | --- |
| e-G1 (X04, X06, X08, X09, X10) only `__setitem__`, `update` and `clear` were pinned as refused; dropping the refusal of `__delitem__`, `pop`, `popitem`, `setdefault` or `__ior__` survived | contract over every mutating dict method (`[]=`, `del`, `pop` with and without a default, `popitem`, `setdefault` on a new and an existing key, `update`, `clear`, `\|=`) on a built and a parsed `ServiceLimit` and a built and a parsed `QuotaPolicy`: each raises `TypeError: extra parameters are read only` and leaves `extra`, and the item's place in a set, unchanged | `test_every_mutating_dict_method_is_refused` (40 cases) |
| e-G2 (X16) dropping `_ReadOnlyDict.__reduce__` survived | contract: `extra` itself pickles under every protocol, copies and deep-copies to the same read-only type, equal and with the same hash, and the copy still refuses changes | `test_extra_pickles_copies_and_stays_read_only` |
| e-G3 (X13) equality with a dict that is not an exact `dict` was unpinned | the GUIDE promise kept and pinned: `extra` equals a `dict`, `Counter`, `OrderedDict` and `defaultdict` with the same items, both ways and with `!=`, and differs from each once a value changes | `test_extra_compares_by_value_with_any_dict` |

Each reported mutant, applied alone to `_extra.py`, fails the new contracts: the refusal of
`__delitem__`, `pop`, `popitem`, `setdefault` and `__ior__` dropped one at a time,
`__reduce__` removed, and the plain-dict branch of `__eq__` returning `NotImplemented` for
anything but an exact `dict`. On 436b63b the new contracts pass, as expected for missing
contracts.

Gates on 2694e2a's tree on another machine, CPython 3.14, with the fetched sources,
http-sf, werkzeug, urllib3, httpx, requests, multidict, pydantic, the 0.2.1 oracle,
`RETRYHEADER_E2E=1` and `RETRYHEADER_E2E_PYPI=1`: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (2780 passed, no skips) all
exit 0.

### Disputed findings (round 7)

None.

## QA round 8 (item 19)

Lens e re-checked 3ce8e68 with ten new mutants on `_ReadOnlyDict`. All three round 7
findings are fixed (each re-mutation fails the new contracts) and nine of the ten new
mutants were killed. One finding, a gap in the contracts and not a behaviour bug, is fixed
in ba7138d and nothing is disputed. No behaviour changed, so the CHANGELOG and GUIDE are
unchanged.

| Finding | Fix | Pinned by |
| --- | --- | --- |
| e-P3 `__ne__` returning `not equal` even when `__eq__` gives `NotImplemented` survived, although it makes `extra != 5` False (with a DeprecationWarning on 3.13, a TypeError on 3.14) | contract with warnings as errors: on a built and a parsed `ServiceLimit` and a built and a parsed `QuotaPolicy`, `extra` differs from an int, `None`, a str, a list of pairs and a `ServiceLimit`, both ways, `==` is False both ways, and `extra.__eq__` and `extra.__ne__` return `NotImplemented` for them like a dict does | `test_extra_differs_from_anything_not_a_mapping` (20 cases) |

The mutant, applied alone to `_extra.py` on CPython 3.13, fails the new contract; on
3ce8e68 the contract passes, as expected for a missing contract.

Gates on ba7138d, a fresh clone on another machine, CPython 3.14: `ruff format --check .`,
`ruff check .`, `mypy --strict src` and `pytest` all exit 0; `mypy --strict` is also clean
on the new test file.

### Disputed findings (round 8)

None.

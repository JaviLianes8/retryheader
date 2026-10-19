# retryheader 1.0.0 author mutation table

The author mutation round of [CERT-1.0-REPORT.md](https://github.com/JaviLianes8/retryheader/blob/main/CERT-1.0-REPORT.md).
Each mutant was applied alone to a copy of the tree at cf9a036 on another machine and the
full suite run with `-x` and a 300 s per-test limit, with the fetched sources, http-sf,
werkzeug, urllib3, httpx, requests, multidict and the 0.2.1 oracle present. 36 of 38 were
killed at once; the two survivors (M25, M36) are killed by contracts added in 7310f6d,
each checked against its mutant.

| Mutant | Module | Change | Killed by |
| --- | --- | --- | --- |
| M01 | `_parse.py` | non-ASCII digits read as delay-seconds | `test_parse.py::test_anything_but_ascii_digits_is_not_delay_seconds[\u0661\u0662]` |
| M02 | `_parse.py` | a past date gives a negative delay | `test_docs.py::test_every_example_runs_and_prints_its_comments[README]` |
| M03 | `_time.py` | tab no longer optional whitespace | `test_docs.py::test_every_example_runs_and_prints_its_comments[GUIDE]` |
| M04 | `_calendar.py` | 50-year boundary off by one | `test_httpdate.py::test_rfc850_two_digit_years_follow_the_50_year_rule[76-2026-2076]` |
| M05 | `_calendar.py` | second 61 read as a leap second | `test_spec_rfc9110.py::test_strict_mode_accepts_exactly_what_the_rfc_allows[2]` |
| M06 | `_calendar.py` | leap second allowed at any minute of hour 23 | `test_spec_rfc9110.py::test_strict_mode_accepts_exactly_what_the_rfc_allows[1]` |
| M07 | `_calendar.py` | zone offset applied with the wrong sign | `test_docs.py::test_every_example_runs_and_prints_its_comments[README]` |
| M08 | `_httpdate.py` | asctime accepts an unpadded one-digit day | `test_spec_rfc9110.py::test_strict_mode_accepts_exactly_what_the_rfc_allows[1]` |
| M09 | `_httpdate.py` | fraction of a second rounds down when formatting | `test_build.py::test_build_from_a_datetime_with_microseconds_rounds_up` |
| M10 | `_httpdate.py` | strict mode stops checking the day name | `test_docs.py::test_every_example_runs_and_prints_its_comments[GUIDE]` |
| M11 | `_lenient.py` | RFC 5322 two-digit year pivot off by one | `test_regressions.py::test_lenient_rfc5322_years_follow_rfc5322[6 Nov 50 08:49:37 +0000-1950]` |
| M12 | `_lenient.py` | zone minutes 60 accepted | `test_httpdate.py::test_dates_without_a_known_zone_or_with_junk_are_rejected[Sun, 06 Nov 1994 08:49:37 +0260]` |
| M13 | `_lenient.py` | numeric zone sign swapped | `test_docs.py::test_every_example_runs_and_prints_its_comments[README]` |
| M14 | `_lenient.py` | PDT offset wrong | `test_spec_rfc5322.py::test_every_named_us_zone_has_the_offset_the_rfc_gives` |
| M15 | `_headers.py` | shortest of several Retry-After | `test_headers.py::test_the_longest_of_several_retry_after_values_wins` |
| M16 | `_headers.py` | Age: 0 treated as served from a cache | `test_headers.py::test_an_age_of_zero_or_an_invalid_age_keeps_the_ratelimit_delay[0]` |
| M17 | `_headers.py` | first of several Date headers used | `test_headers.py::test_an_unusable_date_header_falls_back_to_now` |
| M18 | `_headers.py` | waits with quota left | `test_headers.py::test_quota_left_means_no_wait` |
| M19 | `_headers.py` | shortest exhausted window | `test_clients.py::test_every_field_line_is_read_from_the_library_object[aiohttp]` |
| M20 | `_headers.py` | header names matched with case | `test_clients.py::test_every_field_line_is_read_from_the_library_object[aiohttp]` |
| M21 | `_ratelimit.py` | empty RateLimit-Policy accepted | `test_fuzz.py::test_ratelimit_fields_round_trip_or_fail_whole[101]` |
| M22 | `_ratelimit.py` | wrong default quota unit | `test_docs.py::test_every_example_runs_and_prints_its_comments[README]` |
| M23 | `_ratelimit.py` | pk of RateLimit duplicated into extra | `test_fuzz.py::test_ratelimit_fields_round_trip_or_fail_whole[101]` |
| M24 | `_ratelimit.py` | field lines joined without a comma | `test_clients.py::test_every_field_line_is_read_from_the_library_object[aiohttp]` |
| M25 | `_ratelimit.py` | Boolean accepted as an Integer parameter | `test_ratelimit.py::test_a_boolean_is_not_an_integer_parameter[parse_ratelimit-"a";r=?0-r]` (added after it survived) |
| M26 | `_build.py` | timedelta fraction rounds down | `test_build.py::test_build_from_a_timedelta[value1-2]` |
| M27 | `_build.py` | float delay rounds to nearest | `test_build.py::test_a_fraction_rounds_up_so_the_client_never_returns_early[2.1-3]` |
| M28 | `_sf_scalars.py` | 16-digit Integer accepted | `test_oracles_libs.py::test_list_parsing_matches_http_sf[11]` |
| M29 | `_sf_scalars.py` | string escape of n accepted | `test_sf_suite.py::test_suite_case[string-generated: Escaped 0x6e in string]` |
| M30 | `_sf_scalars.py` | byte sequence of one padding character accepted | `test_oracles_libs.py::test_list_parsing_matches_http_sf[13]` |
| M31 | `_sf_scalars.py` | upper-case percent escapes accepted | `test_sf_suite.py::test_suite_case[display-string: non-ascii display string (uppercase escaping)]` |
| M32 | `_sf.py` | trailing comma accepted | `test_oracles_libs.py::test_list_parsing_matches_http_sf[11]` |
| M33 | `_sf_serialize.py` | lowest Integer refused when building | `test_sf_serialize.py::test_parse_then_serialise_gives_the_canonical_form` (date: syntactic min date) |
| M34 | `_sf_serialize.py` | decimals keep trailing zeros | `test_contract_edges.py::test_the_callers_decimal_context_changes_nothing` |
| M35 | `_sf_serialize.py` | decimals round half up | `test_contract_edges.py::test_the_callers_decimal_context_changes_nothing` |
| M36 | `_errors.py` | error messages quote 4000 characters | `test_contract_edges.py::test_messages_quote_at_most_forty_characters_of_the_input[41]` (added after it survived) |
| M37 | `_ratelimit_types.py` | policy window 0 accepted | `test_docs.py::test_docstring_examples_pass[retryheader]` |
| M38 | `_ratelimit_build.py` | default unit always written | `test_docs.py::test_every_example_runs_and_prints_its_comments[README]` |

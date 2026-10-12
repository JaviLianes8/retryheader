import email
import http.client
from datetime import datetime, timezone

import pytest

from retryheader import delay_from_headers
from tests.fixtures_text import draft_responses

NOW = datetime(2026, 10, 21, 7, 28, 0, tzinfo=timezone.utc)
SKEWED = datetime(2019, 8, 5, 9, 26, 50, tzinfo=timezone.utc)


def test_draft_example_b14_waits_until_the_retry_after_date() -> None:
    headers = draft_responses()[0]
    # Measured from the response's own Date header, whatever the local clock says.
    assert delay_from_headers(headers, now=SKEWED, use_date_header=True) == 5.0
    assert delay_from_headers(headers, now=SKEWED) == 15.0


def test_draft_example_b3_retry_after_wins_over_ratelimit() -> None:
    assert delay_from_headers(draft_responses()[1]) == 20.0


def test_the_fixtures_are_loaded() -> None:
    assert [len(block) for block in draft_responses()] == [4, 4]


def test_names_match_without_regard_to_case() -> None:
    assert delay_from_headers({"RETRY-AFTER": "7"}) == 7.0
    assert delay_from_headers([("retry-after", "7")]) == 7.0


def test_an_exhausted_quota_waits_for_its_effective_window() -> None:
    headers = {"RateLimit": '"a";r=0;t=30, "b";r=5;t=99, "c";r=0;t=45'}
    assert delay_from_headers(headers) == 45.0


def test_quota_left_means_no_wait() -> None:
    assert delay_from_headers({"RateLimit": '"a";r=1;t=30'}) is None


def test_an_exhausted_quota_without_a_window_gives_no_delay() -> None:
    assert delay_from_headers({"RateLimit": '"a";r=0'}) is None


def test_no_relevant_headers_mean_no_wait() -> None:
    assert delay_from_headers({"Content-Type": "text/plain"}) is None
    assert delay_from_headers([]) is None


def test_a_malformed_retry_after_is_ignored() -> None:
    headers = [("Retry-After", "soon"), ("RateLimit", '"a";r=0;t=9')]
    assert delay_from_headers(headers) == 9.0


def test_a_malformed_ratelimit_field_is_ignored_as_a_whole() -> None:
    headers = [("RateLimit", '"a";r=0;t=9'), ("RateLimit", "garbage")]
    assert delay_from_headers(headers) is None


def test_ratelimit_lines_are_combined() -> None:
    headers = [("RateLimit", '"a";r=1;t=9'), ("ratelimit", '"b";r=0;t=12')]
    assert delay_from_headers(headers) == 12.0


def test_the_longest_of_several_retry_after_values_wins() -> None:
    headers = [("Retry-After", "5"), ("Retry-After", "Wed, 21 Oct 2026 07:29:00 GMT")]
    assert delay_from_headers(headers, now=NOW) == 60.0


def test_an_unusable_date_header_falls_back_to_now() -> None:
    value = "Wed, 21 Oct 2026 07:29:00 GMT"
    for date in ("yesterday", None):
        headers = [("Retry-After", value)] + ([("Date", date)] if date else [])
        assert delay_from_headers(headers, now=NOW, use_date_header=True) == 60.0
    twice = [("Retry-After", value), ("Date", value), ("Date", value)]
    assert delay_from_headers(twice, now=NOW, use_date_header=True) == 60.0


def test_the_date_header_does_not_change_delay_seconds() -> None:
    headers = {"Retry-After": "3", "Date": "Wed, 21 Oct 2026 07:00:00 GMT"}
    assert delay_from_headers(headers, now=NOW, use_date_header=True) == 3.0


def test_http_client_messages_are_read_with_repeated_fields() -> None:
    raw = b'RateLimit: "a";r=1;t=1\r\nRateLimit: "b";r=0;t=8\r\n\r\n'
    message = email.message_from_bytes(raw, _class=http.client.HTTPMessage)
    assert delay_from_headers(message) == 8.0


@pytest.mark.parametrize("headers", [None, "Retry-After: 5", b"x", 5, [("Retry-After", 5)]])
def test_unusable_header_containers_are_type_errors(headers: object) -> None:
    with pytest.raises(TypeError):
        delay_from_headers(headers)  # type: ignore[arg-type]


def test_now_must_be_a_datetime() -> None:
    with pytest.raises(TypeError):
        delay_from_headers({}, now=1.0)  # type: ignore[arg-type]

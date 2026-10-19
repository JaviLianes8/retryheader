"""delay_from_headers on the header objects that real HTTP client libraries hand out.

Each container is built by the library itself (from raw header bytes or its own
constructor), not imitated; a test skips when its library is not installed.
"""

from __future__ import annotations

import email.message
import http.client
import io
from collections.abc import Callable
from typing import Any

import pytest

from retryheader import delay_from_headers

RAW = (
    b"HTTP/1.1 429 Too Many Requests\r\n"
    b"Date: Mon, 05 Aug 2019 09:27:00 GMT\r\n"
    b"Retry-After: Mon, 05 Aug 2019 09:27:05 GMT\r\n"
    b'RateLimit: "default";r=0;t=5\r\n'
    b'RateLimit: "daily";r=0;t=86400\r\n'
    b"Content-Type: application/json\r\n\r\n"
)
PAIRS = [
    ("Date", "Mon, 05 Aug 2019 09:27:00 GMT"),
    ("Retry-After", "Mon, 05 Aug 2019 09:27:05 GMT"),
    ("RateLimit", '"default";r=0;t=5'),
    ("RateLimit", '"daily";r=0;t=86400'),
]
NO_RETRY = [pair for pair in PAIRS if pair[0] != "Retry-After"]


def _http_client(pairs: list[tuple[str, str]]) -> Any:
    raw = b"".join(f"{name}: {value}\r\n".encode("latin-1") for name, value in pairs) + b"\r\n"
    return http.client.parse_headers(io.BytesIO(raw))


def _message(pairs: list[tuple[str, str]]) -> Any:
    message = email.message.Message()
    for name, value in pairs:
        message[name] = value
    return message


def _urllib3(pairs: list[tuple[str, str]]) -> Any:
    urllib3 = pytest.importorskip("urllib3")
    headers = urllib3.HTTPHeaderDict()
    for name, value in pairs:
        headers.add(name, value)
    return headers


def _httpx(pairs: list[tuple[str, str]]) -> Any:
    return pytest.importorskip("httpx").Headers(pairs).multi_items()


def _multidict(pairs: list[tuple[str, str]]) -> Any:
    multidict = pytest.importorskip("multidict")  # what aiohttp responses carry
    return multidict.CIMultiDictProxy(multidict.CIMultiDict(pairs))


def _werkzeug(pairs: list[tuple[str, str]]) -> Any:
    return pytest.importorskip("werkzeug.datastructures").Headers(pairs)


BUILDERS: dict[str, Callable[[list[tuple[str, str]]], Any]] = {
    "http.client": _http_client,
    "email.message": _message,
    "urllib3": _urllib3,
    "httpx": _httpx,
    "aiohttp": _multidict,
    "werkzeug": _werkzeug,
}


@pytest.mark.parametrize("library", sorted(BUILDERS))
def test_every_field_line_is_read_from_the_library_object(library: str) -> None:
    headers = BUILDERS[library](PAIRS)
    # The Date header cancels the clock difference; Retry-After wins over RateLimit.
    assert delay_from_headers(headers, use_date_header=True) == 5.0
    # Without Retry-After, both RateLimit lines are read and the longer window wins.
    assert delay_from_headers(BUILDERS[library](NO_RETRY)) == 86400.0


def test_a_real_http_client_response_is_read() -> None:
    sock = _FakeSocket(RAW)
    response = http.client.HTTPResponse(sock)  # type: ignore[arg-type]
    response.begin()
    assert response.status == 429
    assert delay_from_headers(response.headers, use_date_header=True) == 5.0
    assert delay_from_headers(response.getheaders(), use_date_header=True) == 5.0


@pytest.mark.parametrize("library", ["requests", "httpx"])
def test_joined_values_still_read_ratelimit(library: str) -> None:
    # requests and httpx's plain mapping view join repeated lines with ", ". A joined
    # RateLimit is still one valid list; a joined Retry-After is not a valid value.
    if library == "requests":
        structures = pytest.importorskip("requests.structures")
        joined: Any = structures.CaseInsensitiveDict(dict(_urllib3(PAIRS)))
    else:
        joined = pytest.importorskip("httpx").Headers(PAIRS)
    assert joined["RateLimit"] == '"default";r=0;t=5, "daily";r=0;t=86400'
    assert delay_from_headers(joined, use_date_header=True) == 5.0
    twice = dict([*PAIRS[:1], ("Retry-After", "5, 7"), *PAIRS[2:]])
    assert delay_from_headers(twice) == 86400.0


class _FakeSocket:
    """Just enough of a socket for http.client to read a response from bytes."""

    def __init__(self, data: bytes) -> None:
        self._file = io.BytesIO(data)

    def makefile(self, *args: object, **kwargs: object) -> io.BytesIO:
        return self._file

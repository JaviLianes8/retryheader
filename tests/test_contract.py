from __future__ import annotations

import importlib.resources

import retryheader

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "QuotaPolicy",
    "RateLimitError",
    "RetryAfterError",
    "ServiceLimit",
    "build_ratelimit",
    "build_ratelimit_policy",
    "build_retry_after",
    "delay_from_headers",
    "format_http_date",
    "parse_http_date",
    "parse_ratelimit",
    "parse_ratelimit_policy",
    "parse_retry_after",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(retryheader.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in retryheader.__all__:
        assert hasattr(retryheader, name)


def test_version_is_a_three_part_string() -> None:
    parts = retryheader.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("retryheader").joinpath("py.typed").is_file()


def test_every_public_name_is_documented() -> None:
    for name in retryheader.__all__:
        assert getattr(retryheader, name).__doc__, name


def test_errors_are_value_errors() -> None:
    assert issubclass(retryheader.RetryAfterError, ValueError)
    assert issubclass(retryheader.RateLimitError, ValueError)

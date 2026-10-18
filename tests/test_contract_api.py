"""The stable 1.0 API: every public name keeps its signature, defaults and error types."""

from __future__ import annotations

import copy
import dataclasses
import inspect
import pickle
from datetime import datetime, timezone

import pytest

import retryheader
from retryheader import QuotaPolicy, RateLimitError, RetryAfterError, ServiceLimit

KW = inspect.Parameter.KEYWORD_ONLY
POS = inspect.Parameter.POSITIONAL_OR_KEYWORD
EMPTY = inspect.Parameter.empty

# name -> [(parameter, kind, default)], return annotation (postponed annotations: text)
SIGNATURES = {
    "parse_retry_after": (
        [("value", POS, EMPTY), ("now", KW, None), ("strict", KW, False)],
        "float",
    ),
    "build_retry_after": ([("value", POS, EMPTY)], "str"),
    "parse_http_date": (
        [("value", POS, EMPTY), ("now", KW, None), ("strict", KW, False)],
        "datetime",
    ),
    "format_http_date": ([("moment", POS, EMPTY)], "str"),
    "delay_from_headers": (
        [("headers", POS, EMPTY), ("now", KW, None), ("use_date_header", KW, False)],
        "float | None",
    ),
    "parse_ratelimit": ([("value", POS, EMPTY)], "list[ServiceLimit]"),
    "parse_ratelimit_policy": ([("value", POS, EMPTY)], "list[QuotaPolicy]"),
    "build_ratelimit": ([("limits", POS, EMPTY)], "str"),
    "build_ratelimit_policy": ([("policies", POS, EMPTY)], "str"),
}


@pytest.mark.parametrize("name", sorted(SIGNATURES))
def test_function_signatures_are_pinned(name: str) -> None:
    params, returns = SIGNATURES[name]
    signature = inspect.signature(getattr(retryheader, name))
    actual = [(p.name, p.kind, p.default) for p in signature.parameters.values()]
    assert actual == params
    assert signature.return_annotation == returns


def test_the_dataclass_fields_and_defaults_are_pinned() -> None:
    def fields(cls: type) -> list[tuple[str, object]]:
        out = []
        for f in dataclasses.fields(cls):
            default = f.default if f.default_factory is dataclasses.MISSING else "factory"
            out.append((f.name, default))
        return out

    missing = dataclasses.MISSING
    assert fields(QuotaPolicy) == [
        ("name", missing),
        ("quota", missing),
        ("window", None),
        ("unit", "requests"),
        ("partition_key", None),
        ("extra", "factory"),
    ]
    assert fields(ServiceLimit) == [
        ("policy", missing),
        ("remaining", missing),
        ("window", None),
        ("partition_key", None),
        ("extra", "factory"),
    ]


def test_errors_are_value_errors_and_show_as_public_names() -> None:
    for error in (RetryAfterError, RateLimitError):
        assert error.__mro__[1] is ValueError
        assert error.__module__ == "retryheader"
    assert QuotaPolicy.__module__ == ServiceLimit.__module__ == "retryheader"


def test_nothing_public_besides_all() -> None:
    public = sorted(name for name in dir(retryheader) if not name.startswith("_"))
    assert public == sorted(retryheader.__all__)


@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_values_and_errors_pickle_with_every_protocol(protocol: int) -> None:
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    values: list[QuotaPolicy | ServiceLimit] = [
        QuotaPolicy("a", 1, 60, "content-bytes", b"k", {"x": 1.5, "at": at}),
        ServiceLimit("a", 0, 5, b"k", {"flag": True, "s": "x"}),
    ]
    for value in values:
        clone = pickle.loads(pickle.dumps(value, protocol=protocol))
        assert clone == value
        assert dict(clone.extra) == dict(value.extra)
        with pytest.raises(TypeError):
            clone.extra["x"] = 2
    for error in (RetryAfterError("bad"), RateLimitError("bad")):
        clone = pickle.loads(pickle.dumps(error, protocol=protocol))
        assert type(clone) is type(error) and str(clone) == "bad"


def test_pickles_name_the_public_module() -> None:
    assert b"retryheader\x94\x8c\x0cServiceLimit" in pickle.dumps(ServiceLimit("a", 1))


def test_replace_and_copy_validate_and_keep_values() -> None:
    limit = ServiceLimit("a", 1, 5, extra={"x": 1})
    assert copy.copy(limit) == copy.deepcopy(limit) == limit
    assert dataclasses.replace(limit, remaining=0).remaining == 0
    with pytest.raises(ValueError):
        dataclasses.replace(limit, remaining=-1)


def test_equality_includes_extra_but_hashing_does_not() -> None:
    plain, tagged = ServiceLimit("a", 1), ServiceLimit("a", 1, extra={"x": 1})
    assert plain != tagged
    assert hash(plain) == hash(tagged)
    assert len({QuotaPolicy("a", 1), QuotaPolicy("a", 1)}) == 1


def test_values_are_stored_as_plain_builtins() -> None:
    class Name(str):
        pass

    class Count(int):
        pass

    class Key(bytes):
        pass

    limit = ServiceLimit(Name("a"), Count(3), Count(4), Key(b"k"))
    assert type(limit.policy) is str and type(limit.remaining) is int
    assert type(limit.window) is int and type(limit.partition_key) is bytes


def test_the_version_is_1_0_0() -> None:
    assert retryheader.__version__ == "1.0.0"

"""Contracts on the extra mapping itself: read only, picklable and copyable, dict equality."""

from __future__ import annotations

import copy
import pickle
from collections import Counter, OrderedDict, defaultdict
from collections.abc import Callable
from typing import Any

import pytest

from retryheader import QuotaPolicy, ServiceLimit, parse_ratelimit, parse_ratelimit_policy

EXTRA = {"k": 1, "j": 2}


def _items() -> list[ServiceLimit | QuotaPolicy]:
    return [
        ServiceLimit("a", 1, extra=EXTRA),
        parse_ratelimit('"a";r=1;k=1;j=2')[0],
        QuotaPolicy("a", 1, extra=EXTRA),
        parse_ratelimit_policy('"a";q=1;k=1;j=2')[0],
    ]


def _ior(extra: Any) -> None:
    extra |= {"z": 9}


MUTATIONS: list[tuple[str, Callable[[Any], object]]] = [
    ("setitem", lambda e: e.__setitem__("k", 5)),
    ("delitem", lambda e: e.__delitem__("k")),
    ("pop", lambda e: e.pop("k")),
    ("pop-default", lambda e: e.pop("missing", None)),
    ("popitem", lambda e: e.popitem()),
    ("setdefault", lambda e: e.setdefault("z", 9)),
    ("setdefault-existing", lambda e: e.setdefault("k", 9)),
    ("update", lambda e: e.update(z=9)),
    ("clear", lambda e: e.clear()),
    ("ior", _ior),
]


@pytest.mark.parametrize("index", range(4), ids=["built", "parsed", "policy", "parsed-policy"])
@pytest.mark.parametrize(("name", "mutate"), MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_every_mutating_dict_method_is_refused(
    index: int, name: str, mutate: Callable[[Any], object]
) -> None:
    item = _items()[index]
    seen = {item}
    with pytest.raises(TypeError, match="extra parameters are read only"):
        mutate(item.extra)
    assert dict(item.extra) == EXTRA and item.extra == EXTRA and item in seen


@pytest.mark.parametrize("index", range(4), ids=["built", "parsed", "policy", "parsed-policy"])
def test_extra_pickles_copies_and_stays_read_only(index: int) -> None:
    extra: Any = _items()[index].extra
    protocols = range(pickle.HIGHEST_PROTOCOL + 1)
    clones: list[Any] = [pickle.loads(pickle.dumps(extra, p)) for p in protocols]
    clones += [copy.copy(extra), copy.deepcopy(extra)]
    for clone in clones:
        assert type(clone) is type(extra)
        assert clone == extra and dict(clone) == EXTRA and hash(clone) == hash(extra)
        with pytest.raises(TypeError, match="extra parameters are read only"):
            clone["k"] = 5
        with pytest.raises(TypeError, match="extra parameters are read only"):
            del clone["k"]
        assert dict(clone) == EXTRA


@pytest.mark.parametrize(
    "other",
    [dict(EXTRA), Counter(EXTRA), OrderedDict(EXTRA), defaultdict(int, EXTRA)],
    ids=["dict", "Counter", "OrderedDict", "defaultdict"],
)
@pytest.mark.parametrize("index", range(4), ids=["built", "parsed", "policy", "parsed-policy"])
def test_extra_compares_by_value_with_any_dict(index: int, other: dict[str, int]) -> None:
    extra = _items()[index].extra
    assert extra == other and other == extra
    assert (extra != other) is False and (other != extra) is False
    changed = copy.copy(other)
    changed["k"] = 7
    assert extra != changed and changed != extra

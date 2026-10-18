"""The values carried by the RateLimit and RateLimit-Policy fields."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, NoReturn

from ._errors import number, type_name

ParamValue = int | float | str | bytes | bool | datetime


class _ReadOnlyDict(dict[str, ParamValue]):
    """A dict that refuses changes but still pickles, copies and compares like one."""

    def _refuse(self, *args: object, **kwargs: object) -> NoReturn:
        raise TypeError("extra parameters are read only")

    __setitem__ = __delitem__ = _refuse
    clear = pop = popitem = setdefault = update = __ior__ = _refuse

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(frozenset(self.items()))

    def __reduce__(self) -> tuple[Any, ...]:
        return (type(self), (dict(self),))


def _count(owner: object, attr: str, value: object, *, optional: bool, minimum: int) -> None:
    if value is None and optional:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{attr} must be an int, not {type_name(value)}")
    plain = int.__index__(value)
    if plain < minimum:
        raise ValueError(f"{attr} must be at least {minimum}, not {number(plain)}")
    object.__setattr__(owner, attr, plain)


def _text(owner: object, attr: str, value: object, what: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a str, not {type_name(value)}")
    object.__setattr__(owner, attr, str.__str__(value))


def _common(owner: object, partition_key: object, extra: object) -> None:
    if partition_key is not None:
        if not isinstance(partition_key, bytes):
            raise TypeError(f"partition_key must be bytes or None, not {type_name(partition_key)}")
        object.__setattr__(owner, "partition_key", bytes.__getitem__(partition_key, slice(None)))
    if not isinstance(extra, Mapping):
        raise TypeError(f"extra must be a mapping, not {type_name(extra)}")
    copy: dict[str, ParamValue] = {}
    for key, value in extra.items():
        if not isinstance(key, str):
            raise TypeError(f"extra parameter names must be str, not {type_name(key)}")
        if not isinstance(value, (int, float, str, bytes, datetime)):
            raise TypeError(f"unsupported extra parameter value of type {type_name(value)}")
        copy[str.__str__(key)] = value
    # Freeze a private copy so a frozen instance cannot change through the caller's dict.
    object.__setattr__(owner, "extra", _ReadOnlyDict(copy))


@dataclass(frozen=True)
class QuotaPolicy:
    """One quota policy item of a RateLimit-Policy field.

    ``name`` identifies the policy, ``quota`` is the ``q`` parameter (quota units the
    policy allows, at least 0), ``window`` is ``w`` (seconds, at least 1, or None when not
    sent), ``unit`` is ``qu`` (``"requests"`` by default), ``partition_key`` is ``pk`` and
    ``extra`` holds every other parameter, read only. Values are checked on creation:
    TypeError for a wrong type (``bool`` is not an int here), ValueError for a number
    out of range. Instances are frozen, hashable (``extra`` aside) and pickle.

    >>> from retryheader import QuotaPolicy, build_ratelimit_policy
    >>> policy = QuotaPolicy("burst", 100, window=60)
    >>> policy.unit, dict(policy.extra)
    ('requests', {})
    >>> build_ratelimit_policy([policy])
    '"burst";q=100;w=60'
    >>> QuotaPolicy("burst", 100, window=0)
    Traceback (most recent call last):
    ...
    ValueError: window must be at least 1, not 0
    """

    name: str
    quota: int
    window: int | None = None
    unit: str = "requests"
    partition_key: bytes | None = None
    extra: Mapping[str, ParamValue] = field(default_factory=_ReadOnlyDict, hash=False)

    def __post_init__(self) -> None:
        # The order of the checks is the order 0.2 used, so the same error comes first.
        _count(self, "quota", self.quota, optional=False, minimum=0)
        _count(self, "window", self.window, optional=True, minimum=1)
        _text(self, "unit", self.unit, "unit")
        _text(self, "name", self.name, "policy name")
        _common(self, self.partition_key, self.extra)


@dataclass(frozen=True)
class ServiceLimit:
    """One service limit item of a RateLimit field.

    ``policy`` names the quota policy, ``remaining`` is the ``r`` parameter (the
    available quota, at least 0), ``window`` is ``t`` (seconds within which no more than
    ``remaining`` units may be used, at least 0, or None when not sent),
    ``partition_key`` is ``pk`` and ``extra`` holds every other parameter, read only.
    Checked, frozen and hashable like ``QuotaPolicy``.

    >>> from retryheader import ServiceLimit, build_ratelimit
    >>> limit = ServiceLimit("burst", 0, window=30, extra={"acme-tier": "gold"})
    >>> limit.remaining, limit.window, limit.extra["acme-tier"]
    (0, 30, 'gold')
    >>> build_ratelimit([limit])
    '"burst";r=0;t=30;acme-tier="gold"'
    """

    policy: str
    remaining: int
    window: int | None = None
    partition_key: bytes | None = None
    extra: Mapping[str, ParamValue] = field(default_factory=_ReadOnlyDict, hash=False)

    def __post_init__(self) -> None:
        _count(self, "remaining", self.remaining, optional=False, minimum=0)
        _count(self, "window", self.window, optional=True, minimum=0)
        _text(self, "policy", self.policy, "policy name")
        _common(self, self.partition_key, self.extra)

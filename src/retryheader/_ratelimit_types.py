"""The values carried by the RateLimit and RateLimit-Policy fields."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

ParamValue = int | float | str | bytes | bool | datetime
_NO_EXTRA: Mapping[str, ParamValue] = MappingProxyType({})


def _check_count(name: str, value: object, *, optional: bool, minimum: int) -> None:
    if value is None and optional:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, not {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}, not {value}")


def _check_common(owner: object, name: object, partition_key: object, extra: object) -> None:
    if not isinstance(name, str):
        raise TypeError(f"policy name must be a str, not {type(name).__name__}")
    if partition_key is not None and not isinstance(partition_key, bytes):
        raise TypeError("partition_key must be bytes or None")
    if not isinstance(extra, Mapping):
        raise TypeError("extra must be a mapping")
    # Freeze a private copy so a frozen instance cannot change through the caller's dict.
    object.__setattr__(owner, "extra", MappingProxyType(dict(extra)))


@dataclass(frozen=True)
class QuotaPolicy:
    """One quota policy item of a RateLimit-Policy field.

    ``name`` identifies the policy, ``quota`` is the ``q`` parameter (quota units the
    policy allows), ``window`` is ``w`` (seconds, at least 1, or None when not sent),
    ``unit`` is ``qu`` (``"requests"`` by default), ``partition_key`` is ``pk`` and
    ``extra`` holds every other parameter, read only.
    """

    name: str
    quota: int
    window: int | None = None
    unit: str = "requests"
    partition_key: bytes | None = None
    extra: Mapping[str, ParamValue] = field(default=_NO_EXTRA, hash=False)

    def __post_init__(self) -> None:
        _check_count("quota", self.quota, optional=False, minimum=0)
        _check_count("window", self.window, optional=True, minimum=1)
        if not isinstance(self.unit, str):
            raise TypeError(f"unit must be a str, not {type(self.unit).__name__}")
        _check_common(self, self.name, self.partition_key, self.extra)


@dataclass(frozen=True)
class ServiceLimit:
    """One service limit item of a RateLimit field.

    ``policy`` names the quota policy, ``remaining`` is the ``r`` parameter (the
    available quota), ``window`` is ``t`` (seconds within which no more than
    ``remaining`` units may be used, or None when not sent), ``partition_key`` is
    ``pk`` and ``extra`` holds every other parameter, read only.
    """

    policy: str
    remaining: int
    window: int | None = None
    partition_key: bytes | None = None
    extra: Mapping[str, ParamValue] = field(default=_NO_EXTRA, hash=False)

    def __post_init__(self) -> None:
        _check_count("remaining", self.remaining, optional=False, minimum=0)
        _check_count("window", self.window, optional=True, minimum=0)
        _check_common(self, self.policy, self.partition_key, self.extra)

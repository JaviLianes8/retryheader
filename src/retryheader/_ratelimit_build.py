"""Build RateLimit and RateLimit-Policy field values."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone

from ._ratelimit_types import ParamValue, QuotaPolicy, ServiceLimit
from ._sf_serialize import serialize_list
from ._sf_types import BareItem, Date
from ._time import as_utc

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def build_ratelimit_policy(policies: Iterable[QuotaPolicy]) -> str:
    """Render quota policies as a RateLimit-Policy field value.

    ``qu`` is only written when it is not the default ``"requests"``. Raises ValueError
    when there is no policy (the field must be non-empty) or a value cannot be
    represented, TypeError when an item is not a QuotaPolicy.
    """
    members = []
    for policy in policies:
        if not isinstance(policy, QuotaPolicy):
            raise TypeError(f"expected a QuotaPolicy, not {type(policy).__name__}")
        params: dict[str, BareItem] = {"q": policy.quota}
        if policy.unit != "requests":
            params["qu"] = policy.unit
        if policy.window is not None:
            params["w"] = policy.window
        _common(params, policy.partition_key, policy.extra, {"q", "qu", "w", "pk"})
        members.append((policy.name, params))
    if not members:
        raise ValueError("RateLimit-Policy needs at least one policy")
    return serialize_list(members)


def build_ratelimit(limits: Iterable[ServiceLimit]) -> str:
    """Render service limits as a RateLimit field value.

    Raises ValueError when a value cannot be represented, TypeError when an item is
    not a ServiceLimit. No limits give an empty string: omit the field then.
    """
    members = []
    for limit in limits:
        if not isinstance(limit, ServiceLimit):
            raise TypeError(f"expected a ServiceLimit, not {type(limit).__name__}")
        params: dict[str, BareItem] = {"r": limit.remaining}
        if limit.window is not None:
            params["t"] = limit.window
        _common(params, limit.partition_key, limit.extra, {"r", "t", "pk"})
        members.append((limit.policy, params))
    return serialize_list(members)


def _common(
    params: dict[str, BareItem],
    partition_key: bytes | None,
    extra: Mapping[str, ParamValue],
    known: set[str],
) -> None:
    if partition_key is not None:
        params["pk"] = partition_key
    for key, value in extra.items():
        if key in known:
            raise ValueError(f"extra parameter {key!r} clashes with a defined parameter")
        params[key] = _bare(value)


def _bare(value: ParamValue) -> BareItem:
    if not isinstance(value, datetime):
        return value
    delta = as_utc(value) - _EPOCH
    if delta.microseconds:
        raise ValueError("a date parameter must be a whole second")
    return Date(delta.days * 86400 + delta.seconds)

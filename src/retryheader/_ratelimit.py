"""Parse the RateLimit and RateLimit-Policy fields (draft-ietf-httpapi-ratelimit-headers-11)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone
from typing import TypeVar

from ._errors import RateLimitError, quote, type_name
from ._extra import ParamValue
from ._ratelimit_types import QuotaPolicy, ServiceLimit
from ._sf import Member, parse_list
from ._sf_scalars import SFError
from ._sf_types import BareItem, Date, DisplayString, Token

_T = TypeVar("_T")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def parse_ratelimit_policy(value: str | Iterable[str]) -> list[QuotaPolicy]:
    """Parse a RateLimit-Policy field into its quota policies, in order.

    ``value`` is the field value, or every field line of the response in order (they
    are combined with commas, as RFC 9651 requires). Raises RateLimitError when the
    field is malformed: the draft says such a field MUST be ignored as a whole, so no
    partial result is returned. An empty field is malformed too: it must be non-empty.
    Raises TypeError when ``value`` is neither a str nor an iterable of str.

    >>> from retryheader import parse_ratelimit_policy
    >>> for policy in parse_ratelimit_policy('"burst";q=100;w=60, "daily";q=1000'):
    ...     print(policy.name, policy.quota, policy.window, policy.unit)
    burst 100 60 requests
    daily 1000 None requests
    """
    policies = _parse(value, "RateLimit-Policy", _policy)
    if not policies:
        raise RateLimitError("RateLimit-Policy must list at least one policy")
    return policies


def parse_ratelimit(value: str | Iterable[str]) -> list[ServiceLimit]:
    """Parse a RateLimit field into its service limits, in order.

    Accepts the field value or its field lines, like ``parse_ratelimit_policy``. An empty
    field has no limits. Raises RateLimitError when the field is malformed, TypeError
    when ``value`` is neither a str nor an iterable of str.

    >>> from retryheader import parse_ratelimit
    >>> limits = parse_ratelimit(['"burst";r=0;t=30', '"daily";r=900;pk=:dXNlci0x:'])
    >>> [(lim.policy, lim.remaining, lim.window, lim.partition_key) for lim in limits]
    [('burst', 0, 30, None), ('daily', 900, None, b'user-1')]
    """
    return _parse(value, "RateLimit", _limit)


def _parse(
    value: str | Iterable[str], field: str, build: Callable[[str, dict[str, BareItem]], _T]
) -> list[_T]:
    text = _combine(value, field)
    try:
        members = parse_list(text)
    except SFError as exc:
        raise RateLimitError(f"malformed {field} field: {exc}") from exc
    out = []
    for member in members:
        name, params = _named(member, field)
        try:
            out.append(build(name, params))
        except (TypeError, ValueError) as exc:
            raise RateLimitError(f"malformed {field} item {quote(name)}: {exc}") from exc
    return out


def _combine(value: str | Iterable[str], field: str) -> str:
    if isinstance(value, str):
        return str.__str__(value)
    if isinstance(value, (bytes, bytearray)) or not isinstance(value, Iterable):
        raise TypeError(
            f"{field} value must be a str or an iterable of str, not {type_name(value)}"
        )
    lines = list(value)
    if not all(isinstance(line, str) for line in lines):
        raise TypeError(f"{field} field lines must be str")
    return ", ".join(str.__str__(line) for line in lines)


def _is_string(value: object) -> bool:
    # An sf-string, not a Token or Display String, which parse to str subclasses.
    return isinstance(value, str) and not isinstance(value, (Token, DisplayString))


def _named(member: Member, field: str) -> tuple[str, dict[str, BareItem]]:
    value, params = member
    if not _is_string(value):
        raise RateLimitError(f"malformed {field} field: each item must be a String")
    return str(value), params


def _policy(name: str, params: dict[str, BareItem]) -> QuotaPolicy:
    if "q" not in params:
        raise ValueError("the q parameter is required")
    unit = params.get("qu", "requests")
    if not _is_string(unit):
        raise TypeError("qu must be a String")
    return QuotaPolicy(
        name=name,
        quota=_integer(params, "q"),
        window=_optional_integer(params, "w"),
        unit=str(unit),
        partition_key=_partition_key(params),
        extra=_extra(params, {"q", "qu", "w", "pk"}),
    )


def _limit(name: str, params: dict[str, BareItem]) -> ServiceLimit:
    if "r" not in params:
        raise ValueError("the r parameter is required")
    return ServiceLimit(
        policy=name,
        remaining=_integer(params, "r"),
        window=_optional_integer(params, "t"),
        partition_key=_partition_key(params),
        extra=_extra(params, {"r", "t", "pk"}),
    )


def _integer(params: dict[str, BareItem], key: str) -> int:
    value = params[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be an Integer")
    return value


def _optional_integer(params: dict[str, BareItem], key: str) -> int | None:
    return _integer(params, key) if key in params else None


def _partition_key(params: dict[str, BareItem]) -> bytes | None:
    value = params.get("pk")
    if value is not None and not isinstance(value, bytes):
        raise TypeError("pk must be a Byte Sequence")
    return value


def _extra(params: dict[str, BareItem], known: set[str]) -> dict[str, ParamValue]:
    out: dict[str, ParamValue] = {}
    for key, value in params.items():
        if key in known:
            continue
        if isinstance(value, Date):
            try:
                out[key] = _EPOCH + timedelta(seconds=value.seconds)
            except OverflowError as exc:
                raise ValueError(f"date parameter {quote(key)} is out of range") from exc
        else:
            out[key] = value
    return out

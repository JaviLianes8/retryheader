"""Parse the RateLimit and RateLimit-Policy fields (draft-ietf-httpapi-ratelimit-headers-11)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone
from typing import TypeVar

from ._errors import RateLimitError
from ._ratelimit_types import ParamValue, QuotaPolicy, ServiceLimit
from ._sf import Member, parse_list
from ._sf_scalars import SFError
from ._sf_types import BareItem, Date, Token

_T = TypeVar("_T")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def parse_ratelimit_policy(value: str | Iterable[str]) -> list[QuotaPolicy]:
    """Parse a RateLimit-Policy field into its quota policies, in order.

    ``value`` is the field value, or every field line of the response in order (they
    are combined with commas, as RFC 9651 requires). Raises RateLimitError when the
    field is malformed: the draft says such a field MUST be ignored as a whole, so no
    partial result is returned. An empty field is malformed too: it must be non-empty.
    """
    policies = _parse(value, "RateLimit-Policy", _policy)
    if not policies:
        raise RateLimitError("RateLimit-Policy must list at least one policy")
    return policies


def parse_ratelimit(value: str | Iterable[str]) -> list[ServiceLimit]:
    """Parse a RateLimit field into its service limits, in order.

    Accepts the field value or its field lines, like ``parse_ratelimit_policy``.
    Raises RateLimitError when the field is malformed.
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
            raise RateLimitError(f"malformed {field} item {name!r}: {exc}") from exc
    return out


def _combine(value: str | Iterable[str], field: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        raise TypeError(f"{field} value must be a str or an iterable of str, not bytes")
    lines = list(value)
    if not all(isinstance(line, str) for line in lines):
        raise TypeError(f"{field} field lines must be str")
    return ", ".join(lines)


def _named(member: Member, field: str) -> tuple[str, dict[str, BareItem]]:
    value, params = member
    if isinstance(value, Token) or not isinstance(value, str):
        raise RateLimitError(f"malformed {field} field: each item must be a String")
    return str(value), params


def _policy(name: str, params: dict[str, BareItem]) -> QuotaPolicy:
    if "q" not in params:
        raise ValueError("the q parameter is required")
    unit = params.get("qu", "requests")
    if isinstance(unit, Token) or not isinstance(unit, str):
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
                raise ValueError(f"date parameter {key} is out of range") from exc
        else:
            out[key] = value
    return out

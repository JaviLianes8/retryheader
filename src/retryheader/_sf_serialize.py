"""RFC 9651 serialisation (section 4.1) of Lists of Items with parameters."""

from __future__ import annotations

import base64
import math
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_EVEN, Decimal

from ._sf_types import BareItem, Date, DisplayString, Token

_KEY_FIRST = frozenset("abcdefghijklmnopqrstuvwxyz*")
_KEY_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-.*")
_TCHAR = frozenset(
    "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:/"
)
_MAX_INT = 999_999_999_999_999


def serialize_list(members: Iterable[tuple[BareItem, Mapping[str, BareItem]]]) -> str:
    """Serialise a List whose members are all Items."""
    return ", ".join(serialize_bare(value) + serialize_params(params) for value, params in members)


def serialize_params(params: Mapping[str, BareItem]) -> str:
    """Serialise Parameters; a ``True`` value is written as the bare key."""
    out = []
    for key, value in params.items():
        out.append(";" + serialize_key(key))
        if value is not True:
            out.append("=" + serialize_bare(value))
    return "".join(out)


def serialize_key(key: str) -> str:
    if not isinstance(key, str) or not key or key[0] not in _KEY_FIRST:
        raise ValueError(f"invalid structured field key: {key!r}")
    if any(char not in _KEY_CHARS for char in key):
        raise ValueError(f"invalid structured field key: {key!r}")
    return key


def serialize_bare(value: BareItem) -> str:
    """Serialise one bare Item, failing with ValueError or TypeError as 4.1.3.1 says."""
    if isinstance(value, bool):
        return "?1" if value else "?0"
    if isinstance(value, int):
        return _integer(value)
    if isinstance(value, float):
        return _decimal(value)
    if isinstance(value, Token):
        if not value or not (value[0].isascii() and (value[0].isalpha() or value[0] == "*")):
            raise ValueError(f"invalid token: {value!r}")
        if any(char not in _TCHAR for char in value):
            raise ValueError(f"invalid token: {value!r}")
        return str(value)
    if isinstance(value, DisplayString):
        return _display(value)
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, bytes):
        return ":" + base64.b64encode(value).decode("ascii") + ":"
    if isinstance(value, Date):
        return "@" + _integer(value.seconds)
    raise TypeError(f"cannot serialise {type(value).__name__} as a structured field")


def _integer(value: int) -> str:
    if not -_MAX_INT <= value <= _MAX_INT:
        raise ValueError(f"integer out of structured field range: {value}")
    return str(value)


def _decimal(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError(f"decimal must be finite: {value!r}")
    # repr() is the shortest decimal that reads back as this float, so 0.0025 rounds
    # half to even as the decimal 0.0025, not as its binary approximation.
    exact = Decimal(repr(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_EVEN)
    whole, _, fraction = f"{abs(exact):f}".partition(".")
    if len(whole) > 12:
        raise ValueError(f"decimal out of structured field range: {value!r}")
    sign = "-" if exact < 0 else ""
    return f"{sign}{whole}.{fraction.rstrip('0') or '0'}"


def _string(value: str) -> str:
    if any(not " " <= char <= "~" for char in value):
        raise ValueError(f"strings hold printable ASCII only: {value!r}")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _display(value: str) -> str:
    out = ['%"']
    for byte in value.encode("utf-8"):
        char = chr(byte)
        if char in '%"' or not 0x20 <= byte <= 0x7E:
            out.append(f"%{byte:02x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)

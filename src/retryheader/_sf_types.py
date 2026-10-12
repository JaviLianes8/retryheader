"""Value types of RFC 9651 that have no exact Python builtin."""

from __future__ import annotations

from dataclasses import dataclass


class Token(str):
    """An sf-token: an unquoted identifier such as ``foo/bar``."""

    __slots__ = ()


class DisplayString(str):
    """An sf-displaystring: Unicode text sent percent-encoded as ``%"..."``."""

    __slots__ = ()


@dataclass(frozen=True)
class Date:
    """An sf-date: whole seconds since the Unix epoch."""

    seconds: int


BareItem = int | float | str | bytes | bool | Token | DisplayString | Date

"""Value types of RFC 9651 that have no exact Python builtin."""

from __future__ import annotations

from dataclasses import dataclass


class Token(str):
    """An sf-token parameter value: an unquoted identifier such as ``sliding`` or ``a/b``.

    A Token parameter of a RateLimit field parses to this ``str`` subclass, and an
    ``extra`` value of this type is written back unquoted (a plain ``str`` is written as
    a quoted String). The text is checked when a field is built: ValueError for a token
    RFC 9651 does not allow (it starts with a letter or ``*``, then token characters,
    ``:`` or ``/``).

    >>> from retryheader import ServiceLimit, Token, build_ratelimit, parse_ratelimit
    >>> build_ratelimit([ServiceLimit("a", 1, extra={"mode": Token("sliding"), "s": "x"})])
    '"a";r=1;mode=sliding;s="x"'
    >>> type(parse_ratelimit('"a";r=1;mode=sliding')[0].extra["mode"]).__name__
    'Token'
    """

    __slots__ = ()


class DisplayString(str):
    """An sf-displaystring parameter value: Unicode text sent as ``%"..."``.

    A Display String parameter parses to this ``str`` subclass, and an ``extra`` value
    of this type is written back percent-encoded as UTF-8, so it may hold any Unicode
    text UTF-8 can encode. The text is checked when a field is built: ValueError for a
    lone surrogate (a code point from U+D800 to U+DFFF), which has no UTF-8 form.

    >>> from retryheader import DisplayString, ServiceLimit, build_ratelimit
    >>> build_ratelimit([ServiceLimit("a", 1, extra={"note": DisplayString("caf\u00e9")})])
    '"a";r=1;note=%"caf%c3%a9"'
    """

    __slots__ = ()


@dataclass(frozen=True)
class Date:
    """An sf-date: whole seconds since the Unix epoch."""

    seconds: int


BareItem = int | float | str | bytes | bool | Token | DisplayString | Date

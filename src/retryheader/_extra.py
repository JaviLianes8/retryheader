"""The read-only, typed mapping that holds the extra parameters of a limit or policy."""

from __future__ import annotations

from datetime import datetime
from typing import Any, NoReturn

from ._errors import number, type_name
from ._sf_types import DisplayString, Token
from ._time import plain_datetime

# The largest Integer a structured field can carry (RFC 9651 section 3.3.1).
_MAX_INT = 999_999_999_999_999

ParamValue = int | float | str | bytes | bool | datetime


class _ReadOnlyDict(dict[str, ParamValue]):
    """A dict that refuses changes but still pickles, copies and compares like one."""

    __slots__ = ("_sealed",)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if getattr(self, "_sealed", False):
            self._refuse()
        super().__init__(*args, **kwargs)
        self._sealed = True

    def _refuse(self, *args: object, **kwargs: object) -> NoReturn:
        raise TypeError("extra parameters are read only")

    __setitem__ = __delitem__ = _refuse
    clear = pop = popitem = setdefault = update = __ior__ = _refuse

    def _typed(self) -> frozenset[tuple[str, type, ParamValue]]:
        return frozenset((key, type(value), value) for key, value in self.items())

    def __eq__(self, other: object) -> bool:
        # Between two extras the structured-field type counts (True, 1 and 1.0, or a
        # Token and a String, are written differently); a plain dict compares by value.
        if isinstance(other, _ReadOnlyDict):
            return self._typed() == other._typed()
        return dict.__eq__(self, other)

    def __ne__(self, other: object) -> bool:
        equal = self.__eq__(other)
        return equal if equal is NotImplemented else not equal

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(self._typed())

    def __reduce__(self) -> tuple[Any, ...]:
        return (type(self), (dict(self),))


def plain_value(value: object) -> ParamValue:
    # Copy into the exact built-in type (Token and DisplayString keep their own), so a
    # subclass's __repr__, __hash__ or __str__ never reaches repr(), hash() or the output.
    if isinstance(value, bool):
        return value is True
    if isinstance(value, int):
        plain = int.__index__(value)
        if not -_MAX_INT <= plain <= _MAX_INT:
            raise ValueError(
                f"an integer extra parameter has at most 15 digits, not {number(plain)}"
            )
        return plain
    if isinstance(value, float):
        return float.__float__(value)
    if isinstance(value, (Token, DisplayString)):
        kind = Token if isinstance(value, Token) else DisplayString
        return kind(str.__str__(value))
    if isinstance(value, str):
        return str.__str__(value)
    if isinstance(value, bytes):
        return bytes.__getitem__(value, slice(None))
    if isinstance(value, datetime):
        return plain_datetime(value)
    raise TypeError(f"unsupported extra parameter value of type {type_name(value)}")

"""Time and text helpers shared by parsing and building."""

from __future__ import annotations

from datetime import datetime, timezone

from ._errors import type_name

# RFC 9110 section 5.6.3: optional whitespace in a field is SP or HTAB, nothing else.
_OWS = " \t"


def as_utc(moment: datetime) -> datetime:
    """Return moment as aware UTC (naive means UTC); ValueError past year 1 or 9999."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        return moment.replace(tzinfo=timezone.utc)
    try:
        return moment.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError("datetime has no UTC equivalent between years 1 and 9999") from exc


def check_datetime(moment: object) -> None:
    """Raise TypeError unless moment is a datetime."""
    if not isinstance(moment, datetime):
        raise TypeError(f"expected a datetime, not {type_name(moment)}")


def check_text(value: object, what: str) -> str:
    """Return ``value`` as a plain ``str``; TypeError for anything else.

    A ``str`` subclass is copied into a plain ``str`` first, so its own methods (``strip``,
    ``__eq__``, ``__repr__``) can never change how it is read.
    """
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a str, not {type_name(value)}")
    return str.__str__(value)


def strip_ows(text: str) -> str:
    """Remove the optional whitespace HTTP allows around a field value."""
    return text.strip(_OWS)

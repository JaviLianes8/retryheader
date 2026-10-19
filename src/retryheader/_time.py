"""Time and text helpers shared by parsing and building."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ._errors import type_name

# RFC 9110 section 5.6.3: optional whitespace in a field is SP or HTAB, nothing else.
_OWS = " \t"


def plain_datetime(moment: datetime) -> datetime:
    """Copy a datetime into a plain ``datetime`` through the base class descriptors.

    A subclass is read as its stored value, so its own ``year``, ``weekday`` or
    ``__format__`` can never change what is parsed or written.
    """
    return datetime(
        date.year.__get__(moment),
        date.month.__get__(moment),
        date.day.__get__(moment),
        datetime.hour.__get__(moment),
        datetime.minute.__get__(moment),
        datetime.second.__get__(moment),
        datetime.microsecond.__get__(moment),
        datetime.tzinfo.__get__(moment),
        fold=datetime.fold.__get__(moment),
    )


def whole_seconds(delta: timedelta) -> tuple[int, int]:
    """Return (seconds, microseconds) of a timedelta, read through the base descriptors."""
    days = timedelta.days.__get__(delta)
    return days * 86400 + timedelta.seconds.__get__(delta), timedelta.microseconds.__get__(delta)


def as_utc(moment: datetime, what: str = "datetime") -> datetime:
    """Return moment as a plain aware UTC datetime (naive means UTC).

    ValueError when its UTC moment falls outside years 1 to 9999.
    """
    moment = plain_datetime(moment)
    if moment.tzinfo is None or moment.utcoffset() is None:
        return moment.replace(tzinfo=timezone.utc)
    try:
        return moment.astimezone(timezone.utc)
    except OverflowError as exc:
        raise ValueError(f"{what} has no UTC equivalent between years 1 and 9999") from exc


def check_now(now: object) -> datetime | None:
    """Check the reference time once on entry and return it as UTC (None stays None).

    TypeError when it is not a datetime, ValueError when it has no UTC equivalent, so
    the error never depends on which form of header the server sent.
    """
    if now is None:
        return None
    if not isinstance(now, datetime):
        raise TypeError(f"expected a datetime, not {type_name(now)}")
    return as_utc(now, "now")


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

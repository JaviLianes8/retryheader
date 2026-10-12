"""Time and text helpers shared by parsing and building."""

from __future__ import annotations

from datetime import datetime, timezone

# RFC 9110 section 5.6.3: optional whitespace in a field is SP or HTAB, nothing else.
_OWS = " \t"


def as_utc(moment: datetime) -> datetime:
    """Return moment as an aware UTC datetime, assuming UTC when it is naive."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def check_datetime(moment: object) -> None:
    """Raise TypeError unless moment is a datetime."""
    if not isinstance(moment, datetime):
        raise TypeError(f"expected a datetime, not {type(moment).__name__}")


def strip_ows(text: str) -> str:
    """Remove the optional whitespace HTTP allows around a field value."""
    return text.strip(_OWS)

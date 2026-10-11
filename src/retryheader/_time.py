"""Time helpers shared by parsing and building."""

from __future__ import annotations

from datetime import datetime, timezone


def as_utc(moment: datetime) -> datetime:
    """Return moment as an aware UTC datetime, assuming UTC when it is naive."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)

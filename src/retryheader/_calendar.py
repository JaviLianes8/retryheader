"""Turn validated date fields into an aware UTC datetime."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ._errors import RetryAfterError, quote
from ._time import as_utc

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def assemble(
    *,
    year: int | None,
    yy: int | None,
    month: int,
    day: int,
    clock: tuple[int, int, int],
    offset: int,
    now: datetime | None,
    text: str,
    weekday: int | None = None,
) -> datetime:
    """Build the UTC moment, resolving a two-digit year and a leap second.

    ``offset`` is the zone offset in minutes east of UTC. ``weekday`` (Monday is 0), when
    given, must be the day of the week of the written date.
    """
    hour, minute, second = clock
    # A leap second ends a minute; datetime cannot hold it, so it becomes the first
    # second of the next minute. datetime() rejects every other out-of-range field.
    leap = second == 60
    if year is None:
        year = resolve_two_digit_year(yy or 0, (month, day, hour, minute, second), now)
    try:
        local = datetime(year, month, day, hour, minute, 59 if leap else second)
        moment = local - timedelta(minutes=offset)
    except (ValueError, OverflowError) as exc:
        raise RetryAfterError(f"impossible date: {quote(text)}") from exc
    # RFC 5322 section 3.3, whose semantics RFC 9110 adopts: the day name is the day the
    # date falls on.
    if weekday is not None and local.weekday() != weekday:
        raise RetryAfterError(f"the day name does not match the date: {quote(text)}")
    # Leap seconds are only ever inserted at 23:59:60 UTC (RFC 9110 5.6.7).
    if leap and (moment.hour, moment.minute) != (23, 59):
        raise RetryAfterError(f"a leap second can only be 23:59:60 UTC: {quote(text)}")
    if leap:
        try:
            moment += timedelta(seconds=1)
        except OverflowError as exc:  # 9999-12-31 23:59:60 has no next second
            raise RetryAfterError(f"impossible date: {quote(text)}") from exc
    return moment.replace(tzinfo=timezone.utc)


def resolve_two_digit_year(
    yy: int, rest: tuple[int, int, int, int, int], now: datetime | None
) -> int:
    """Pick the century for a two-digit year with the RFC 9110 50-year rule.

    A year that appears to be more than 50 years in the future is the most recent
    past year with the same last two digits. ``rest`` is (month, day, hour, minute,
    second).
    """
    reference = as_utc(now) if now is not None else datetime.now(timezone.utc)
    limit = (reference.year + 50, *reference.timetuple()[1:6])
    year = reference.year - reference.year % 100 + yy
    if (year, *rest) > limit:
        year -= 100
    elif (year + 100, *rest) <= limit:
        year += 100
    return year

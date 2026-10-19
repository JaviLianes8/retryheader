"""Contracts for how the reference time and its subclasses are read: fold, offsets, descriptors."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

from retryheader import build_retry_after, parse_retry_after

UTC = timezone.utc
EST, EDT = timedelta(hours=-5), timedelta(hours=-4)


class _NewYorkFallBack(tzinfo):
    """Hand-written model of America/New_York around 2026-11-01, when 01:00-02:00 repeats.

    The first pass of the repeated hour (fold=0) is EDT and the second (fold=1) is EST,
    as PEP 495 says; outside that hour the offset is EST, which is all these tests need.
    """

    def utcoffset(self, dt: datetime | None) -> timedelta:
        assert dt is not None
        repeated = dt.replace(tzinfo=None, fold=0)
        if datetime(2026, 11, 1, 1) <= repeated < datetime(2026, 11, 1, 2):
            return EST if dt.fold else EDT
        return EST

    def dst(self, dt: datetime | None) -> timedelta:
        return self.utcoffset(dt) - EST

    def tzname(self, dt: datetime | None) -> str:
        return "EDT" if self.dst(dt) else "EST"


def test_an_ambiguous_now_is_read_with_the_offset_its_fold_picks() -> None:
    target = "Sun, 01 Nov 2026 07:00:00 GMT"
    first = datetime(2026, 11, 1, 1, 30, tzinfo=_NewYorkFallBack())
    second = datetime(2026, 11, 1, 1, 30, fold=1, tzinfo=_NewYorkFallBack())
    assert parse_retry_after(target, now=first) == 5400.0  # 05:30 UTC
    assert parse_retry_after(target, now=second) == 1800.0  # 06:30 UTC


class _NoOffset(tzinfo):
    """An aware-looking tzinfo that knows no offset: Python treats the value as naive."""

    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> None:
        return None


def test_a_now_whose_tzinfo_has_no_offset_is_read_as_utc_not_local_time() -> None:
    # Whatever the host's time zone, a value without an offset means UTC, as naive does.
    now = datetime(2026, 1, 1, 12, tzinfo=_NoOffset())
    assert parse_retry_after("Thu, 01 Jan 2026 12:01:00 GMT", now=now) == 60.0
    assert parse_retry_after("Thu, 01 Jan 2026 12:01:00 GMT", now=now.replace(tzinfo=None)) == 60.0


class _LyingDelta(timedelta):
    @property
    def days(self) -> int:
        return 5

    @property
    def seconds(self) -> int:
        return 0

    @property
    def microseconds(self) -> int:
        return 1


def test_a_timedelta_subclass_is_read_through_the_base_descriptors() -> None:
    assert build_retry_after(_LyingDelta(seconds=90)) == "90"
    assert build_retry_after(_LyingDelta(days=1, seconds=1, microseconds=1)) == "86402"


class _LyingZone(datetime):
    @property
    def tzinfo(self) -> tzinfo:
        return timezone(timedelta(hours=5))

    @property
    def fold(self) -> int:
        return 1


def test_a_datetime_subclass_is_read_with_its_stored_tzinfo_and_fold() -> None:
    now = _LyingZone(2026, 1, 1, 12, tzinfo=UTC)
    assert parse_retry_after("Thu, 01 Jan 2026 12:01:00 GMT", now=now) == 60.0
    ambiguous = _LyingZone(2026, 11, 1, 1, 30, tzinfo=_NewYorkFallBack())
    assert parse_retry_after("Sun, 01 Nov 2026 07:00:00 GMT", now=ambiguous) == 5400.0

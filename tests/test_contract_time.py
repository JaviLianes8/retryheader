"""Contracts for how the reference time and its subclasses are read: fold, offsets, descriptors."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path

import retryheader
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


_ON_A_HOST_THREE_HOURS_AHEAD = """
from datetime import datetime, tzinfo
from retryheader import parse_retry_after
class NoOffset(tzinfo):
    def utcoffset(self, dt): return None
    def dst(self, dt): return None
    def tzname(self, dt): return None
local = datetime(2026, 1, 1, 12).astimezone().utcoffset().total_seconds()
now = datetime(2026, 1, 1, 12, tzinfo=NoOffset())
print(local, parse_retry_after("Thu, 01 Jan 2026 12:01:00 GMT", now=now))
"""


def test_a_now_with_no_offset_ignores_the_host_time_zone_even_on_a_utc_host() -> None:
    # The host here may be on UTC, where local time and UTC agree; a child process with a
    # zone three hours ahead (honoured by both POSIX and the Windows C runtime) tells them apart.
    src = str(Path(retryheader.__file__).resolve().parent.parent)
    env = {**os.environ, "TZ": "UTC-3", "PYTHONPATH": src}
    run = subprocess.run(
        [sys.executable, "-c", _ON_A_HOST_THREE_HOURS_AHEAD],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert run.stdout.split() == ["10800.0", "60.0"]


class _FiveHoursAheadNoName(tzinfo):
    """A real offset with no name and no DST: the offset alone decides the moment."""

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return timedelta(hours=5)

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> None:
        return None


def test_a_now_with_an_offset_but_no_zone_name_is_read_with_its_offset() -> None:
    now = datetime(2026, 1, 1, 12, tzinfo=_FiveHoursAheadNoName())  # 07:00 UTC
    assert parse_retry_after("Thu, 01 Jan 2026 12:01:00 GMT", now=now) == 18060.0


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
    """Every component lies; only the stored value may be read."""

    @property
    def year(self) -> int:
        return 2025

    @property
    def month(self) -> int:
        return 6

    @property
    def day(self) -> int:
        return 2

    @property
    def hour(self) -> int:
        return 3

    @property
    def minute(self) -> int:
        return 0

    @property
    def second(self) -> int:
        return 0

    @property
    def microsecond(self) -> int:
        return 0

    @property
    def tzinfo(self) -> tzinfo:
        return timezone(timedelta(hours=5))

    @property
    def fold(self) -> int:
        return 1


def test_a_datetime_subclass_is_read_with_its_stored_components() -> None:
    now = _LyingZone(2026, 1, 1, 12, 5, 30, 500_000, tzinfo=UTC)
    assert parse_retry_after("Thu, 01 Jan 2026 12:10:00 GMT", now=now) == 269.5
    assert build_retry_after(now) == "Thu, 01 Jan 2026 12:05:31 GMT"  # rounded up
    ambiguous = _LyingZone(2026, 11, 1, 1, 30, tzinfo=_NewYorkFallBack())
    assert parse_retry_after("Sun, 01 Nov 2026 07:00:00 GMT", now=ambiguous) == 5400.0

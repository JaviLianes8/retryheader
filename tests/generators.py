"""Seeded generators of header values, valid and hostile, shared by the fuzz tests."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ZONES = ["GMT", "UT", "UTC", "EST", "PDT", "+0200", "-0130", "+9959", "Z", "CET", "+0060", ""]
NOISE = " \t\r\n,;:=\"'()-+./0123456789aAzZ@%?*\\\x00\x7f\u00a0\u0661\u212a\ud800"
SF_PIECES = [
    '"a"',
    "tok",
    "?1",
    "?0",
    "1",
    "-12",
    "1.5",
    "1.2345",
    ":aGVsbG8=:",
    ":=:",
    "@17",
    '%"f%c3%bc"',
    ";r=0",
    ";r=-1",
    ";t=30",
    ";w=0",
    ";q=5",
    ';qu="x"',
    ";pk=:YQ==:",
    ";k",
    ", ",
    ",",
    "(",
    ")",
    " ",
    "\t",
    "=",
    '"',
    "%",
    "r=1",
]


def http_date(rng: random.Random) -> str:
    """One date in a random format, field values sometimes out of range."""
    moment = datetime(1970, 1, 1) + timedelta(seconds=rng.randrange(-(10**9), 5 * 10**9))
    day = moment.day if rng.random() < 0.9 else rng.randrange(0, 40)
    name = DAYS[moment.weekday()] if rng.random() < 0.8 else rng.choice(DAYS)
    mon = MONTHS[moment.month - 1]
    second = moment.second if rng.random() < 0.9 else rng.choice([60, 61, 99])
    clock = f"{moment.hour:02d}:{moment.minute:02d}:{second:02d}"
    form = rng.randrange(5)
    if form == 0:
        return f"{name[:3]}, {day:02d} {mon} {moment.year:04d} {clock} GMT"
    if form == 1:
        return f"{name}, {day:02d}-{mon}-{moment.year % 100:02d} {clock} GMT"
    if form == 2:
        return f"{name[:3]} {mon} {day:2d} {clock} {moment.year:04d}"
    if form == 3:
        return f"{name[:3]}, {day} {mon} {moment.year} {clock} {rng.choice(ZONES)}".rstrip()
    return f"{day} {mon} {moment.year % 1000} {clock[:5]} {rng.choice(ZONES)}".rstrip()


def mutate(rng: random.Random, text: str, edits: int = 2) -> str:
    """Insert, delete or change a few characters, or change their case."""
    chars = list(text)
    for _ in range(rng.randrange(edits + 1)):
        spot = rng.randrange(len(chars) + 1)
        action = rng.randrange(4)
        if action == 0:
            chars.insert(spot, rng.choice(NOISE))
        elif chars and action == 1:
            del chars[min(spot, len(chars) - 1)]
        elif chars and action == 2:
            chars[min(spot, len(chars) - 1)] = rng.choice(NOISE)
        elif chars:
            index = min(spot, len(chars) - 1)
            chars[index] = chars[index].swapcase()
    return "".join(chars)


def retry_after(rng: random.Random) -> str:
    """A Retry-After value: delay-seconds, a date or noise, often around whitespace."""
    kind = rng.randrange(4)
    if kind == 0:
        value = str(rng.randrange(10 ** rng.randrange(1, 25)))
    elif kind == 1:
        value = http_date(rng)
    elif kind == 2:
        value = mutate(rng, http_date(rng))
    else:
        value = "".join(rng.choice(NOISE) for _ in range(rng.randrange(12)))
    return rng.choice(["", " ", "\t"]) + value + rng.choice(["", " ", "\t "])


def sf_field(rng: random.Random) -> str:
    """A RateLimit-like field: mostly well-formed items, sometimes broken."""
    if rng.random() < 0.5:
        items = []
        for _ in range(rng.randrange(1, 4)):
            name = rng.choice(['"a"', '"burst"', '"day"', "tok", '%"x"'])
            params = rng.sample(
                [";r=0", ";r=7", ";t=30", ";q=5", ";w=60", ";pk=:YQ==:", ";x=?1"], 3
            )
            items.append(name + "".join(params))
        return rng.choice([", ", ",", " , "]).join(items)
    return "".join(rng.choice(SF_PIECES) for _ in range(rng.randrange(1, 8)))


def now(rng: random.Random) -> datetime:
    """A reference time, aware or naive."""
    moment = datetime(2026, 10, 21, tzinfo=timezone.utc) + timedelta(seconds=rng.randrange(10**8))
    return moment if rng.random() < 0.8 else moment.replace(tzinfo=None)

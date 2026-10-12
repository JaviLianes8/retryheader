"""Readers for the verbatim specification fixtures in tests/fixtures."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _lines(name: str) -> list[str]:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line and not line.startswith("#")]


def rfc9110_retry_after() -> list[str]:
    """The Retry-After field values of RFC 9110 section 10.2.3."""
    prefix = "Retry-After: "
    return [
        line[len(prefix) :] for line in _lines("rfc9110-examples.txt") if line.startswith(prefix)
    ]


def rfc9110_dates() -> list[str]:
    """The three HTTP-date examples of RFC 9110 section 5.6.7, comments removed."""
    lines = [line for line in _lines("rfc9110-examples.txt") if ";" in line]
    return [line.split(";")[0].rstrip() for line in lines]


def draft_fields(field: str) -> list[str]:
    """Every value of one field in the RateLimit draft examples.

    The field value excludes the optional whitespace after the colon (RFC 9110 5.5);
    one draft line has none.
    """
    out = []
    for line in _lines("ratelimit-draft-11.txt"):
        name, _, value = line.partition(":")
        if name == field:
            out.append(value.strip(" 	"))
    return out


def draft_responses() -> list[list[tuple[str, str]]]:
    """The header blocks of the draft's B.1.4 and B.3 examples, as (name, value) pairs."""
    text = (FIXTURES / "ratelimit-draft-11-responses.txt").read_text(encoding="utf-8")
    blocks = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if ": " in line and not line.startswith("#")]
        blocks.append([(name, value) for name, _, value in (ln.partition(": ") for ln in lines)])
    return blocks

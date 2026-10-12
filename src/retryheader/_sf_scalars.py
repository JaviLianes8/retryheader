"""RFC 9651 scalar parsers: numbers, strings, byte sequences, display strings."""

from __future__ import annotations

import base64
import binascii
import re

from ._sf_types import DisplayString

_BASE64 = re.compile(r"[A-Za-z0-9+/=]*")
_DIGITS = "0123456789"


class SFError(ValueError):
    """The text is not a valid Structured Field of the requested type."""


class Cursor:
    """A position in an ASCII field value, consumed left to right."""

    def __init__(self, text: str) -> None:
        if not text.isascii():
            raise SFError("structured fields are ASCII")
        self.text = text
        self.pos = 0

    def peek(self) -> str:
        return self.text[self.pos : self.pos + 1]

    def take(self) -> str:
        char = self.peek()
        self.pos += 1
        return char

    def skip(self, chars: str) -> None:
        while self.peek() and self.peek() in chars:
            self.pos += 1

    def done(self) -> bool:
        return self.pos >= len(self.text)


def parse_number(cur: Cursor) -> int | float:
    """Section 4.2.4: an Integer (15 digits) or a Decimal (12.3 digits)."""
    sign = 1
    if cur.peek() == "-":
        cur.take()
        sign = -1
    if not cur.peek() or cur.peek() not in _DIGITS:
        raise SFError("a number needs a digit")
    digits = ""
    decimal = False
    while cur.peek():
        char = cur.peek()
        if char in _DIGITS:
            digits += char
        elif char == "." and not decimal:
            if len(digits) > 12:
                raise SFError("decimal integer part too long")
            digits += char
            decimal = True
        else:
            break
        cur.take()
        if len(digits) > (16 if decimal else 15):
            raise SFError("number too long")
    if not decimal:
        return sign * int(digits)
    if digits.endswith(".") or len(digits) - digits.index(".") - 1 > 3:
        raise SFError("a decimal has one to three fractional digits")
    return sign * float(digits)


def parse_string(cur: Cursor) -> str:
    """Section 4.2.5: a quoted string of printable ASCII with two escapes."""
    cur.take()
    out: list[str] = []
    while not cur.done():
        char = cur.take()
        if char == "\\":
            escaped = cur.take()
            if escaped not in ('"', "\\"):
                raise SFError("only quote and backslash can be escaped")
            out.append(escaped)
        elif char == '"':
            return "".join(out)
        elif not " " <= char <= "~":
            raise SFError("strings hold printable ASCII only")
        else:
            out.append(char)
    raise SFError("unterminated string")


def parse_bytes(cur: Cursor) -> bytes:
    """Section 4.2.7: base64 between colons."""
    cur.take()
    end = cur.text.find(":", cur.pos)
    if end < 0:
        raise SFError("unterminated byte sequence")
    content = cur.text[cur.pos : end]
    cur.pos = end + 1
    if not _BASE64.fullmatch(content):
        raise SFError("byte sequences are base64")
    try:
        # Padding is synthesised and pad bits are not checked, as section 4.2.7 asks.
        bare = content.rstrip("=")
        return base64.b64decode(bare + "=" * (-len(bare) % 4), validate=True)
    except binascii.Error as exc:
        raise SFError("invalid base64") from exc


def parse_display(cur: Cursor) -> DisplayString:
    """Section 4.2.10: percent-encoded UTF-8 between %" and "."""
    if cur.text[cur.pos : cur.pos + 2] != '%"':
        raise SFError('a display string starts with %"')
    cur.pos += 2
    raw = bytearray()
    while not cur.done():
        char = cur.take()
        if not " " <= char <= "~":
            raise SFError("display strings hold printable ASCII only")
        if char == '"':
            try:
                return DisplayString(raw.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise SFError("display string is not UTF-8") from exc
        if char == "%":
            pair = cur.text[cur.pos : cur.pos + 2]
            cur.pos += 2
            if len(pair) != 2 or any(c not in "0123456789abcdef" for c in pair):
                raise SFError("percent escapes are two lowercase hex digits")
            raw.append(int(pair, 16))
        else:
            raw.append(ord(char))
    raise SFError("unterminated display string")

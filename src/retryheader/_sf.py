"""RFC 9651 Structured Field parsing for Lists and Items (section 4.2)."""

from __future__ import annotations

from ._sf_scalars import Cursor, SFError, parse_bytes, parse_display, parse_number, parse_string
from ._sf_types import BareItem, Date, Token

Params = dict[str, BareItem]
Item = tuple[BareItem, Params]
InnerList = tuple[list[Item], Params]
Member = Item | InnerList

_TCHAR = "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_TOKEN_CHARS = frozenset(_TCHAR + ":/")
_KEY_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-.*")


def parse_list(text: str) -> list[Member]:
    """Parse a whole field value as a List (empty input is an empty list)."""
    cur = Cursor(text)
    cur.skip(" ")
    members: list[Member] = []
    while not cur.done():
        members.append(_inner_list(cur) if cur.peek() == "(" else _item(cur))
        cur.skip(" \t")
        if cur.done():
            return members
        if cur.take() != ",":
            raise SFError("expected a comma between list members")
        cur.skip(" \t")
        if cur.done():
            raise SFError("trailing comma")
    return members


def parse_item(text: str) -> Item:
    """Parse a whole field value as an Item."""
    cur = Cursor(text)
    cur.skip(" ")
    item = _item(cur)
    cur.skip(" ")
    if not cur.done():
        raise SFError("unexpected text after the item")
    return item


def _inner_list(cur: Cursor) -> InnerList:
    cur.take()
    items: list[Item] = []
    while not cur.done():
        cur.skip(" ")
        if cur.peek() == ")":
            cur.take()
            return items, _params(cur)
        items.append(_item(cur))
        if cur.peek() not in (" ", ")"):
            raise SFError("inner list members are separated by spaces")
    raise SFError("unterminated inner list")


def _item(cur: Cursor) -> Item:
    return _bare(cur), _params(cur)


def _params(cur: Cursor) -> Params:
    params: Params = {}
    while cur.peek() == ";":
        cur.take()
        cur.skip(" ")
        key = _key(cur)
        value: BareItem = True
        if cur.peek() == "=":
            cur.take()
            value = _bare(cur)
        params[key] = value
    return params


def _key(cur: Cursor) -> str:
    first = cur.peek()
    if not (first == "*" or "a" <= first <= "z"):
        raise SFError("a key starts with a lowercase letter or '*'")
    start = cur.pos
    while cur.peek() and cur.peek() in _KEY_CHARS:
        cur.pos += 1
    return cur.text[start : cur.pos]


def _bare(cur: Cursor) -> BareItem:
    first = cur.peek()
    if first == "-" or (first != "" and first in "0123456789"):
        return parse_number(cur)
    if first == '"':
        return parse_string(cur)
    if first == "*" or (first != "" and first.isalpha()):
        return _token(cur)
    if first == ":":
        return parse_bytes(cur)
    if first == "?":
        cur.take()
        flag = cur.take()
        if flag not in ("0", "1"):
            raise SFError("a boolean is ?0 or ?1")
        return flag == "1"
    if first == "@":
        cur.take()
        seconds = parse_number(cur)
        if not isinstance(seconds, int):
            raise SFError("a date is an integer")
        return Date(seconds)
    if first == "%":
        return parse_display(cur)
    raise SFError(f"unrecognised item at offset {cur.pos}")


def _token(cur: Cursor) -> Token:
    start = cur.pos
    cur.pos += 1
    while cur.peek() and cur.peek() in _TOKEN_CHARS:
        cur.pos += 1
    return Token(cur.text[start : cur.pos])

"""A small ABNF (RFC 5234) to regular expression converter for the rules of a spec text.

It understands what the HTTP-date, delay-seconds and OWS rules of RFC 9110 use:
case-sensitive ``%s"..."`` and case-insensitive ``"..."`` strings, ``%xHH`` values,
``n``, ``n*m`` and ``*`` repetition, alternation, grouping and rule references, plus the
core rules SP, HTAB and DIGIT. Rules are read from the text itself, never typed in here.
"""

from __future__ import annotations

import re

CORE = {"SP": " ", "HTAB": "\\t", "DIGIT": "[0-9]"}
Tokens = list[dict[str, str | None]]
_TOKEN = re.compile(
    r'\s*(?:(?P<rep>\d*\*\d*|\d+)?(?:(?P<cs>%s"[^"]*")|(?P<ci>"[^"]*")|(?P<hex>%x[0-9A-Fa-f]+)'
    r"|(?P<name>[A-Za-z][A-Za-z0-9-]*)|(?P<open>\()|(?P<close>\))|(?P<alt>/)))"
)


def rules(text: str) -> dict[str, str]:
    """Collect ``name = definition`` rules from a spec text, continuation lines joined."""
    found: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        body = line.split(";", 1)[0] if not re.search(r'"[^"]*;[^"]*"', line) else line
        match = re.match(r"^\s+([A-Za-z][A-Za-z0-9-]*)\s+=\s+(.*)$", body)
        if match:
            current = match.group(1)
            found[current] = match.group(2).strip()
        elif current and re.match(r"^\s+/", body):
            found[current] += " " + body.strip()
        elif body.strip():
            current = None
    return found


def to_regex(name: str, grammar: dict[str, str]) -> str:
    """Return a regular expression (no anchors) for one rule and everything it uses."""
    if name in CORE:
        return CORE[name]
    tokens = list(_tokens(grammar[name]))
    pattern, rest = _alternation(tokens, grammar)
    assert not rest, f"unparsed tokens in {name}: {rest}"
    return pattern


def _tokens(definition: str) -> Tokens:
    out = []
    position = 0
    while position < len(definition.rstrip()):
        match = _TOKEN.match(definition, position)
        assert match and match.end() > position, f"cannot read ABNF at {definition[position:]!r}"
        out.append(match.groupdict())
        position = match.end()
    return out


def _alternation(tokens: Tokens, grammar: dict[str, str]) -> tuple[str, Tokens]:
    branches = []
    while True:
        branch, tokens = _concatenation(tokens, grammar)
        branches.append(branch)
        if not tokens or not tokens[0]["alt"]:
            return "(?:" + "|".join(branches) + ")", tokens
        tokens = tokens[1:]


def _concatenation(tokens: Tokens, grammar: dict[str, str]) -> tuple[str, Tokens]:
    parts = []
    while tokens and not tokens[0]["alt"] and not tokens[0]["close"]:
        token, tokens = tokens[0], tokens[1:]
        if token["open"]:
            inner, tokens = _alternation(tokens, grammar)
            assert tokens and tokens[0]["close"], "unbalanced parentheses"
            tokens = tokens[1:]
            element = inner
        elif token["cs"]:
            element = "(?:" + re.escape(token["cs"][3:-1]) + ")"
        elif token["ci"]:
            literal = token["ci"][1:-1]
            element = (
                "(?:"
                + "".join(
                    f"[{c.lower()}{c.upper()}]" if c.isalpha() else re.escape(c) for c in literal
                )
                + ")"
            )
        elif token["hex"]:
            element = re.escape(chr(int(token["hex"][2:], 16)))
        else:
            element = "(?:" + to_regex(str(token["name"]), grammar) + ")"
        parts.append(element + _repeat(token["rep"]))
    return "".join(parts), tokens


def _repeat(rep: str | None) -> str:
    if not rep:
        return ""
    if "*" not in rep:
        return "{" + rep + "}"
    low, _, high = rep.partition("*")
    return "{" + (low or "0") + "," + high + "}"

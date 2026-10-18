"""Error types for retryheader, and the helpers that keep their messages short."""

from __future__ import annotations

_LIMIT = 40


class RetryAfterError(ValueError):
    """Raised when a Retry-After value or an HTTP-date cannot be parsed.

    A ``ValueError``, so ``except ValueError`` catches it too. The message quotes at most
    40 characters of the input.

    >>> from retryheader import RetryAfterError, parse_retry_after
    >>> try:
    ...     parse_retry_after("soon")
    ... except RetryAfterError as error:
    ...     print(error, isinstance(error, ValueError))
    invalid Retry-After value: 'soon' True
    """


class RateLimitError(ValueError):
    """Raised when a RateLimit or RateLimit-Policy field is malformed.

    A ``ValueError``. The draft says a malformed field MUST be ignored as a whole, so the
    parsers raise this instead of returning part of the field.

    >>> from retryheader import RateLimitError, parse_ratelimit
    >>> try:
    ...     parse_ratelimit('"burst";r=-1')
    ... except RateLimitError as error:
    ...     print(error)
    malformed RateLimit item 'burst': remaining must be at least 0, not -1
    """


def quote(text: str) -> str:
    """Return ``repr(text)``, cut to 40 characters so a huge input stays out of messages."""
    text = str.__str__(text)
    if len(text) <= _LIMIT:
        return repr(text)
    return f"{text[:_LIMIT]!r}... ({len(text)} characters)"


def type_name(value: object) -> str:
    """Return the name of the type of ``value``, cut to 40 characters."""
    name = str(type(value).__name__)
    return name if len(name) <= _LIMIT else name[: _LIMIT - 3] + "..."


def number(value: int) -> str:
    """Return ``str(value)`` for a readable integer, otherwise its size in bits."""
    value = int.__index__(value)
    if value.bit_length() <= 128:
        return str(value)
    return f"an integer of {value.bit_length()} bits"

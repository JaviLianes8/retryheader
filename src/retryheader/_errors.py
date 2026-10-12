"""Error types for retryheader."""

from __future__ import annotations


class RetryAfterError(ValueError):
    """Raised when a Retry-After value or an HTTP-date cannot be parsed."""


class RateLimitError(ValueError):
    """Raised when a RateLimit or RateLimit-Policy field is malformed."""

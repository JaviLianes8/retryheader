"""Error types for retryheader."""

from __future__ import annotations


class RetryAfterError(ValueError):
    """Raised when a Retry-After value cannot be parsed."""

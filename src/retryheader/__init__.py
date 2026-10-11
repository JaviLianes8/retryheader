"""Parse and build the HTTP Retry-After header, both forms, zero dependencies and typed."""

from __future__ import annotations

from ._build import build_retry_after
from ._errors import RetryAfterError
from ._parse import parse_retry_after

__version__ = "0.1.0"

__all__ = ["RetryAfterError", "build_retry_after", "parse_retry_after"]

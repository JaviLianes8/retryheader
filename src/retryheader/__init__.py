"""Parse and build Retry-After, HTTP-date, RateLimit and RateLimit-Policy, zero dependencies."""

from __future__ import annotations

from ._build import build_retry_after
from ._errors import RateLimitError, RetryAfterError
from ._headers import delay_from_headers
from ._httpdate import format_http_date, parse_http_date
from ._parse import parse_retry_after
from ._ratelimit import parse_ratelimit, parse_ratelimit_policy
from ._ratelimit_build import build_ratelimit, build_ratelimit_policy
from ._ratelimit_types import QuotaPolicy, ServiceLimit

__version__ = "0.2.0"

__all__ = [
    "QuotaPolicy",
    "RateLimitError",
    "RetryAfterError",
    "ServiceLimit",
    "build_ratelimit",
    "build_ratelimit_policy",
    "build_retry_after",
    "delay_from_headers",
    "format_http_date",
    "parse_http_date",
    "parse_ratelimit",
    "parse_ratelimit_policy",
    "parse_retry_after",
]

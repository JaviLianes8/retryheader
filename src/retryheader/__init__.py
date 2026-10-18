"""Parse and build Retry-After, HTTP-date, RateLimit and RateLimit-Policy, zero dependencies.

>>> from retryheader import delay_from_headers
>>> delay_from_headers({"Retry-After": "120"})
120.0
"""

# No "from __future__ import annotations" here: it would leave a public name behind.
from ._build import build_retry_after
from ._errors import RateLimitError, RetryAfterError
from ._headers import delay_from_headers
from ._httpdate import format_http_date, parse_http_date
from ._parse import parse_retry_after
from ._ratelimit import parse_ratelimit, parse_ratelimit_policy
from ._ratelimit_build import build_ratelimit, build_ratelimit_policy
from ._ratelimit_types import QuotaPolicy, ServiceLimit

__version__ = "1.0.0"

# The public classes show and pickle as retryheader.<Name>, so a pickle never depends on
# the private module that defines them (pickles made by 0.2 still load: the classes stay
# where 0.2 defined them).
for _cls in (QuotaPolicy, RateLimitError, RetryAfterError, ServiceLimit):
    _cls.__module__ = __name__
del _cls

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

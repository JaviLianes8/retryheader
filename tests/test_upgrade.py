"""The PyPI release 0.2.1 as an oracle: 1.0.0 answers the same, except where documented.

Set RETRYHEADER_V021 to a folder holding the 0.2.1 package (the unpacked wheel:
`pip download retryheader==0.2.1 --no-deps`, then unzip it); the tests skip otherwise.
"""

from __future__ import annotations

import importlib.util
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import retryheader
from tests.generators import now, retry_after, sf_field

NOW = datetime(2026, 10, 21, 7, 28, tzinfo=timezone.utc)
_NAMED_ZONE = re.compile(r"\d(UT|UTC|GMT|[ECMP][SD]T)\s*$", re.IGNORECASE)


@pytest.fixture(scope="module")
def old() -> ModuleType:
    folder = os.environ.get("RETRYHEADER_V021")
    if not folder:
        pytest.skip("set RETRYHEADER_V021 to the unpacked 0.2.1 release")
    init = Path(folder) / "retryheader" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "retryheader_v021", init, submodule_search_locations=[str(init.parent)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["retryheader_v021"] = module
    if sys.version_info < (3, 11):
        # The bug fixed in 1.0.0: 0.2.1 cannot even be imported on Python 3.10.
        with pytest.raises(ValueError, match="mutable default"):
            spec.loader.exec_module(module)
        pytest.skip("0.2.1 does not import on Python 3.10")
    spec.loader.exec_module(module)
    assert module.__version__ == "0.2.1"
    return module


def _outcome(module: ModuleType, name: str, *args: Any, **kwargs: Any) -> Any:
    try:
        result = getattr(module, name)(*args, **kwargs)
    except (TypeError, ValueError) as error:
        # The message of the cause too: parse_retry_after wraps the date error.
        message = f"{error} | {error.__cause__ or ''}"
        return ("error", type(error).__name__, message if len(message) < 240 else "")
    if isinstance(result, list):
        return [
            (
                type(r).__name__,
                *[getattr(r, f) for f in r.__dataclass_fields__ if f != "extra"],
                sorted((k, type(v).__name__, v) for k, v in r.extra.items()),
            )
            for r in result
        ]
    return result


def _documented_date_change(new: Any, before: Any, text: str, strict: bool) -> bool:
    failed = isinstance(new, tuple) and new[0] == "error"
    if failed and "day name does not match" in new[2]:
        return strict  # strict mode checks the day name now
    if failed and "leap second can only be" in new[2]:
        return bool(before[:2] == new[:2])  # same error, the message names the real problem
    # Erratum 6639: a named zone may follow the time without a space (default mode only).
    was_refused = isinstance(before, tuple) and before[0] == "error"
    return not strict and not failed and was_refused and bool(_NAMED_ZONE.search(text))


def test_dates_and_delays_agree_with_0_2_1(old: ModuleType) -> None:
    rng = random.Random(41)
    compared = 0
    for _ in range(12000):
        text, strict, reference = retry_after(rng), rng.random() < 0.5, now(rng)
        for name in ("parse_retry_after", "parse_http_date"):
            kwargs = {"now": reference, "strict": strict}
            new, before = (
                _outcome(retryheader, name, text, **kwargs),
                _outcome(old, name, text, **kwargs),
            )
            if new != before:
                assert _documented_date_change(new, before, text.strip(" \t"), strict), (
                    name,
                    text,
                    new,
                    before,
                )
            compared += 1
    assert compared == 24000


def test_ratelimit_fields_agree_with_0_2_1(old: ModuleType) -> None:
    rng = random.Random(42)
    for _ in range(12000):
        field = sf_field(rng)
        for name in ("parse_ratelimit", "parse_ratelimit_policy"):
            new, before = _outcome(retryheader, name, field), _outcome(old, name, field)
            if new != before:
                # Display Strings where a String is required, and padding-only byte sequences.
                assert new[:2] == ("error", "RateLimitError"), (field, new, before)
                assert '%"' in field or ":=:" in field, (field, new, before)
        headers = [("RateLimit", field), ("Retry-After", retry_after(rng))]
        if rng.random() < 0.2:
            headers.append(("Age", rng.choice(["0", "5", "x"])))
        new, before = (
            _outcome(m, "delay_from_headers", headers, now=NOW) for m in (retryheader, old)
        )
        if new != before:
            dropped = '%"' in field or ":=:" in field or ("Age", "5") in headers
            zone = bool(_NAMED_ZONE.search(headers[1][1].strip(" 	")))
            assert (dropped and new is None) or (zone and before != new), (headers, new, before)


def test_builders_agree_with_0_2_1(old: ModuleType) -> None:
    rng = random.Random(43)
    for _ in range(3000):
        seconds = rng.choice([rng.uniform(-10, 10**9), rng.randrange(-5, 10**12)])
        assert retryheader.build_retry_after(seconds) == old.build_retry_after(seconds)
        moment = now(rng)
        assert retryheader.format_http_date(moment) == old.format_http_date(moment)
        field = sf_field(rng)
        try:
            limits = old.parse_ratelimit(field)
        except ValueError:
            continue
        fields = [[getattr(x, f) for f in x.__dataclass_fields__] for x in limits]
        rebuilt = [retryheader.ServiceLimit(*values) for values in fields]
        new, before = (
            _outcome(retryheader, "build_ratelimit", rebuilt),
            _outcome(old, "build_ratelimit", limits),
        )
        assert new == before if isinstance(new, str) else new[:2] == before[:2]

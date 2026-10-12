"""The public API is typed: mypy infers the results and rejects wrong arguments."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

api = pytest.importorskip("mypy.api")

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from retryheader import (
    build_ratelimit, delay_from_headers, parse_http_date, parse_ratelimit,
    parse_ratelimit_policy, parse_retry_after,
)

reveal_type(parse_retry_after("120"))
reveal_type(parse_http_date("Sun, 06 Nov 1994 08:49:37 GMT"))
reveal_type(parse_ratelimit('"a";r=1'))
reveal_type(parse_ratelimit_policy('"a";q=1')[0].window)
reveal_type(delay_from_headers({"Retry-After": "5"}))
parse_retry_after(120)
build_ratelimit(["a"])
delay_from_headers({"Retry-After": 5})
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    out, err, _ = api.run(
        ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    )
    return str(out) + str(err)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (7, "float"),
        (8, "datetime.datetime"),
        (9, "list[retryheader._ratelimit_types.ServiceLimit]"),
        (10, "int | None"),
        (11, "float | None"),
    ],
)
def test_results_are_typed(mypy_output: str, line: int, expected: str) -> None:
    match = re.search(rf"snippet\.py:{line}: note: Revealed type is \"(.+)\"", mypy_output)
    assert match, mypy_output
    # Older mypy releases spell builtins with their module prefix and unions as Union.
    revealed = match.group(1).replace("builtins.", "")
    revealed = re.sub(r"Union\[(.+), None\]", r"\1 | None", revealed)
    assert revealed == expected


@pytest.mark.parametrize("line", [12, 13, 14])
def test_wrong_argument_types_are_rejected(mypy_output: str, line: int) -> None:
    assert re.search(
        rf"snippet\.py:{line}: error: .*\[(arg-type|list-item|dict-item)\]", mypy_output
    ), mypy_output

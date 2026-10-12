"""The README examples run and print what their comments say; metadata agrees."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import retryheader

ROOT = Path(__file__).resolve().parents[1]

TRANSCRIPT = """\
120.0
30.0
None
15.0
5.0
120.0
120.0
120.0
120.0
0.0
invalid Retry-After value: '-5'
3
120
Wed, 21 Oct 2026 07:28:00 GMT
1994-11-06 08:49:37+00:00
2060
2027-01-01 00:00:00+00:00
1994-11-06 08:49:37+00:00
Sun, 06 Nov 1994 08:49:37 GMT
burst 100 60 requests
daily 1000 86400 requests
0 30
{'acme-tier': 'gold'}
ignored: malformed RateLimit item 'burst': remaining must be at least 0, not -1
"burst";q=100;w=60
"burst";r=0;t=30;pk=:dXNlci0x:
"""


def _readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def _python_blocks() -> list[str]:
    return re.findall(r"```python\n(.*?)```", _readme(), flags=re.DOTALL)


def test_every_readme_example_runs_and_prints_the_transcript(
    capsys: pytest.CaptureFixture[str],
) -> None:
    blocks = _python_blocks()
    assert len(blocks) == 5
    for block in blocks:
        exec(compile(block, "README.md", "exec"), {"__name__": "readme"})
    assert capsys.readouterr().out == TRANSCRIPT


def test_every_printed_comment_is_real_output() -> None:
    # "print(...)  # value" promises a line of output; a stale comment fails here.
    printed = set(TRANSCRIPT.splitlines())
    checked = 0
    for block in _python_blocks():
        for line in block.splitlines():
            if line.lstrip().startswith("print(") and "  # " in line:
                comment = line.split("  # ", 1)[1]
                comment = comment.split(", never")[0].split(": fractions")[0]
                assert comment in printed, line
                checked += 1
    assert checked == 22


def test_every_public_name_appears_in_the_readme() -> None:
    for name in retryheader.__all__:
        assert name in _readme(), name


def test_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == retryheader.__version__


def test_changelog_has_an_entry_for_this_version() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{retryheader.__version__}]" in text

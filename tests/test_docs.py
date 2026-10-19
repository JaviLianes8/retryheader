"""The docs run: README and GUIDE examples print what they say, docstring examples pass.

Also the house rules a reader relies on: absolute links in the README, versions that
agree, no em dash and no source file over 200 lines.
"""

from __future__ import annotations

import contextlib
import doctest
import importlib
import io
import pkgutil
import re
from pathlib import Path

import pytest

import retryheader

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "GUIDE.md").read_text(encoding="utf-8")
MODULES = ["retryheader"] + [
    f"retryheader.{module.name}" for module in pkgutil.iter_modules(retryheader.__path__)
]


def _python_blocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)


def _expected_output(block: str) -> list[str]:
    """The comment lines right after a print hold what it prints, one line each."""
    expected: list[str] = []
    after_print = False
    for line in block.splitlines():
        stripped = line.strip()
        if after_print and stripped.startswith("# "):
            expected.append(stripped[2:])
        else:
            after_print = "print(" in stripped
    return expected


def _printed(block: str) -> list[str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(block, "docs", "exec"), {"__name__": "docs"})
    return out.getvalue().splitlines()


@pytest.mark.parametrize(
    ("text", "blocks", "lines"), [(README, 5, 21), (GUIDE, 3, 10)], ids=["README", "GUIDE"]
)
def test_every_example_runs_and_prints_its_comments(text: str, blocks: int, lines: int) -> None:
    found = _python_blocks(text)
    assert len(found) == blocks
    checked = 0
    for block in found:
        expected = _expected_output(block)
        assert expected, block
        assert _printed(block) == expected, block
        checked += len(expected)
    assert checked == lines


@pytest.mark.parametrize("name", MODULES)
def test_docstring_examples_pass(name: str) -> None:
    module = importlib.import_module(name)
    result = doctest.testmod(module, optionflags=doctest.ELLIPSIS)
    assert result.failed == 0


def test_every_public_name_has_a_docstring_example() -> None:
    finder = doctest.DocTestFinder()
    for name in retryheader.__all__:
        tests = finder.find(getattr(retryheader, name), name)
        assert any(test.examples for test in tests), name


def test_the_readme_links_are_absolute_and_reach_the_guide_and_changelog() -> None:
    for target in re.findall(r"\]\(([^)]+)\)", README):
        assert target.startswith("https://"), target
    assert "GUIDE.md" in README and "CHANGELOG.md" in README
    assert "lianes8studio.com/certified" in README


def test_every_public_name_appears_in_the_docs() -> None:
    for name in retryheader.__all__:
        assert name in README or name in GUIDE, name


def test_versions_agree() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)
    assert match is not None and match.group(1) == retryheader.__version__
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(
        rf"^## \[{re.escape(retryheader.__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.M
    )


def test_no_em_dash_and_no_long_source_file() -> None:
    for path in ROOT.rglob("*"):
        parts = path.relative_to(ROOT).parts
        if not path.is_file() or path.suffix not in {".py", ".md", ".toml", ".ps1", ".json"}:
            continue
        if any(part.startswith(".") or part in ("__pycache__", "build", "dist") for part in parts):
            continue
        if parts[:2] == ("tests", "upstream") and path.name != "MANIFEST.json":
            continue
        assert chr(0x2014) not in path.read_text(encoding="utf-8"), path
        if path.suffix == ".py":
            assert path.read_text(encoding="utf-8").count("\n") <= 200, path

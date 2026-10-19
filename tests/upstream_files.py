"""Access to the third-party files listed in tests/upstream/MANIFEST.json.

The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their tests
skip while the files are absent and fail if a file differs from the manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"
MANIFEST: dict[str, dict[str, Any]] = json.loads(
    (UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8")
)
SKIP_REASON = "upstream files are not fetched; run python scripts/fetch_upstream.py"
_SUITE = "httpwg/structured-field-tests"


def fetched() -> bool:
    """True when every file in the manifest is present."""
    return all((UPSTREAM / name).is_file() for name in MANIFEST)


def read(name: str) -> bytes:
    """Return one fetched file, failing loudly if it differs from the manifest."""
    body = (UPSTREAM / name).read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    assert digest == MANIFEST[name]["sha256"], f"{name} differs from MANIFEST.json"
    return body


def json_files(prefix: str = "") -> list[tuple[str, Any]]:
    """Every fetched suite ``*.json`` directly under ``prefix``, parsed, sorted by name."""
    if not fetched():
        return []
    names = [
        name
        for name, entry in MANIFEST.items()
        if _SUITE in entry["url"] and name.endswith(".json") and name.rpartition("/")[0] == prefix
    ]
    return [(Path(n).stem, json.loads(read(n))) for n in sorted(names)]


def text(name: str) -> str:
    """Return a fetched text (an RFC or a draft) without its page furniture.

    Skips the calling test when the file is absent. Page footers, headers and form feeds
    are removed so that a paragraph split by a page break reads as one.
    """
    if not (UPSTREAM / name).is_file():
        pytest.skip(SKIP_REASON)
    body = read(name).decode("utf-8-sig")
    lines = [
        line
        for line in body.replace("\f", "").splitlines()
        if not re.match(r"^(\S.*\[Page \d+\]|RFC \d+ .*\d{4}|Internet-Draft .*\d{4})$", line)
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def section(body: str, heading: str) -> str:
    """Return the text of one numbered section, from its heading to the next heading."""
    start = re.search(rf"^{re.escape(heading)}$", body, flags=re.MULTILINE)
    assert start is not None, heading
    end = re.search(r"^(?:\d+|[A-Z])(?:\.\d+)*\.  \S", body[start.end() :], flags=re.MULTILINE)
    return body[start.end() : start.end() + end.start()] if end else body[start.end() :]


def sentence(body: str, words: str) -> str:
    """Return the sentence of ``body`` that contains ``words``, whitespace collapsed."""
    flat = re.sub(r"\s+", " ", body)
    index = flat.find(words)
    assert index >= 0, words
    begin = flat.rfind(". ", 0, index)
    end = flat.find(". ", index)
    return flat[0 if begin < 0 else begin + 2 : len(flat) if end < 0 else end + 1]

"""Access to the third-party test files listed in tests/upstream/MANIFEST.json.

The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their tests
skip while the files are absent and fail if a file differs from the manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

UPSTREAM = Path(__file__).resolve().parent / "upstream"
MANIFEST: dict[str, dict[str, Any]] = json.loads(
    (UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8")
)
SKIP_REASON = "upstream files are not fetched; run python scripts/fetch_upstream.py"


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
    """Every fetched ``*.json`` directly under ``prefix``, parsed, sorted by name."""
    if not fetched():
        return []
    names = [n for n in MANIFEST if n.endswith(".json") and n.rpartition("/")[0] == prefix]
    return [(Path(n).stem, json.loads(read(n))) for n in sorted(names)]

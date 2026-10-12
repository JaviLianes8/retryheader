"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with RETRYHEADER_E2E=1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("RETRYHEADER_E2E") != "1", reason="set RETRYHEADER_E2E=1 to build and install"
)

PROGRAM = r"""
import email, http.client, importlib.metadata, importlib.resources
from datetime import datetime, timedelta, timezone
import retryheader
from retryheader import *

assert "site-packages" in retryheader.__file__, retryheader.__file__
assert importlib.metadata.version("retryheader") == retryheader.__version__
assert importlib.resources.files("retryheader").joinpath("py.typed").is_file()

now = datetime(2026, 10, 21, 7, 28, tzinfo=timezone.utc)
for text in ("Wed, 21 Oct 2026 07:30:00 GMT", "Wednesday, 21-Oct-26 07:30:00 GMT",
             "Wed Oct 21 07:30:00 2026"):
    assert parse_retry_after(text, now=now, strict=True) == 120.0, text
assert parse_http_date("Monday, 01-Jan-60 00:00:00 GMT", now=now).year == 2060
assert build_retry_after(2.5) == "3"
assert build_retry_after(timedelta(seconds=1, microseconds=1)) == "2"
try:
    parse_retry_after("Wed, 21 Oct 2026 07:30:00")
except RetryAfterError:
    pass
else:
    raise AssertionError("zone-less date accepted")

policies = parse_ratelimit_policy('"burst";q=100;w=60, "daily";q=1000;w=86400')
assert parse_ratelimit_policy(build_ratelimit_policy(policies)) == policies
limits = parse_ratelimit(['"a";r=0;t=30', '"b";r=5;pk=:QXBwLTk5OQ==:'])
assert limits[1] == ServiceLimit("b", 5, None, b"App-999")
try:
    parse_ratelimit('"a";r=-1')
except RateLimitError:
    pass
else:
    raise AssertionError("negative quota accepted")

raw = (b"Date: Mon, 05 Aug 2019 09:27:00 GMT\r\n"
       b"Retry-After: Mon, 05 Aug 2019 09:27:05 GMT\r\n"
       b'RateLimit: "default";r=0;t=5\r\n\r\n')
message = email.message_from_bytes(raw, _class=http.client.HTTPMessage)
assert delay_from_headers(message, use_date_header=True) == 5.0
assert delay_from_headers({"RateLimit": '"a";r=0;t=9'}) == 9.0
print("e2e ok")
"""


def _run(*cmd: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--wheel", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("retryheader-*.whl")

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "e2e ok"

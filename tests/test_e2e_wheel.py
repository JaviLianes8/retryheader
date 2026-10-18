"""Build the wheel and sdist, install the wheel in throwaway venvs and use it from outside.

Slow and needs the build backend, so it runs only with RETRYHEADER_E2E=1; the upgrade from
the PyPI release also needs RETRYHEADER_E2E_PYPI=1 (it downloads retryheader 0.2.1).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

from tests.e2e_program import PROBE, PROGRAM

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("RETRYHEADER_E2E") != "1", reason="set RETRYHEADER_E2E=1 to build and install"
)


def _run(*cmd: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, check=False, timeout=600
    )


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("dist")
    built = _run(sys.executable, "-m", "build", "--outdir", out, ROOT)
    assert built.returncode == 0, built.stderr
    return out


def _venv(folder: Path) -> Path:
    venv.create(folder, with_pip=True)
    return folder / ("Scripts" if sys.platform == "win32" else "bin") / "python"


def test_wheel_and_sdist_contents(dist: Path) -> None:
    (wheel,) = dist.glob("retryheader-1.0.0-py3-none-any.whl")
    names = zipfile.ZipFile(wheel).namelist()
    assert "retryheader/py.typed" in names and "retryheader/__init__.py" in names
    assert any(name.endswith(".dist-info/licenses/LICENSE") for name in names)
    assert all(name.startswith(("retryheader/", "retryheader-1.0.0.dist-info/")) for name in names)
    metadata = zipfile.ZipFile(wheel).read("retryheader-1.0.0.dist-info/METADATA").decode()
    assert "Requires-Dist" not in metadata and "Requires-Python: >=3.10" in metadata
    assert "Classifier: Development Status :: 5 - Production/Stable" in metadata
    (sdist,) = dist.glob("retryheader-1.0.0.tar.gz")
    with tarfile.open(sdist) as archive:
        listing = [name.split("/", 1)[1] for name in archive.getnames() if "/" in name]
    for present in ("GUIDE.md", "LICENSE", "tests/upstream/MANIFEST.json", "tests/abnf.py"):
        assert present in listing, present
    upstream = [name for name in listing if name.startswith("tests/upstream/")]
    assert upstream == ["tests/upstream/MANIFEST.json"]
    for absent in ("CERT-1.0", "IMPROVEMENTS", "__pycache__", ".github", "tests/fixtures/"):
        assert not any(absent in name for name in listing), absent


def test_installed_wheel_end_to_end(dist: Path, tmp_path: Path) -> None:
    (wheel,) = dist.glob("retryheader-*.whl")
    python = _venv(tmp_path / "venv")
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr
    # Run from an empty folder in isolated mode so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "e2e ok"


@pytest.mark.skipif(
    os.environ.get("RETRYHEADER_E2E_PYPI") != "1", reason="set RETRYHEADER_E2E_PYPI=1 to use PyPI"
)
def test_upgrade_in_place_from_the_pypi_release(dist: Path, tmp_path: Path) -> None:
    (wheel,) = dist.glob("retryheader-*.whl")
    python = _venv(tmp_path / "venv")
    old = _run(python, "-m", "pip", "install", "-q", "retryheader==0.2.1")
    assert old.returncode == 0, old.stderr
    before = _run(python, "-I", "-c", PROBE, cwd=tmp_path)
    if sys.version_info < (3, 11):
        assert "mutable default" in before.stderr  # 0.2.1 never imported on 3.10
    else:
        assert before.returncode == 0, before.stderr
        assert before.stdout.splitlines()[0] == "0.2.1"
    upgraded = _run(python, "-m", "pip", "install", "-q", "--upgrade", wheel)
    assert upgraded.returncode == 0, upgraded.stderr
    after = _run(python, "-I", "-c", PROBE, cwd=tmp_path)
    assert after.returncode == 0, after.stderr
    assert after.stdout.splitlines()[0] == "1.0.0"
    if sys.version_info >= (3, 11):
        # Same answers, and the pickle 0.2.1 wrote loads in 1.0.0 (the probe checks it).
        assert after.stdout.splitlines()[1:-1] == before.stdout.splitlines()[1:-1]
        loaded = _run(python, "-I", "-c", PROBE, before.stdout.splitlines()[-1], cwd=tmp_path)
        assert loaded.returncode == 0 and "pickle ok" in loaded.stdout, loaded.stderr
        old_venv = _venv(tmp_path / "old")
        assert _run(old_venv, "-m", "pip", "install", "-q", "retryheader==0.2.1").returncode == 0
        back = _run(old_venv, "-I", "-c", PROBE, after.stdout.splitlines()[-1], cwd=tmp_path)
        assert back.returncode == 0 and "pickle ok" in back.stdout, back.stderr
    work = tmp_path / "work"
    work.mkdir()
    final = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert final.returncode == 0 and final.stdout.strip() == "e2e ok", final.stderr

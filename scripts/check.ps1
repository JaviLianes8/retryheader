# Local quality gate. Run before every commit. No CI runs in the cloud.
# $ErrorActionPreference does NOT stop on a native command's non-zero exit, so each tool's
# exit code is checked explicitly: a red gate must fail, never pass silently.
# Optional: python scripts/fetch_upstream.py first (specifications and the structured field
# suite), RETRYHEADER_E2E=1 to build and install the wheel, RETRYHEADER_E2E_PYPI=1 to also
# upgrade from the PyPI release, RETRYHEADER_V021=<unpacked 0.2.1 wheel> for the 0.2.1 oracle.
$ErrorActionPreference = "Stop"

function Invoke-Step($label, [scriptblock]$cmd) {
    Write-Host "== $label =="
    & $cmd
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $label (exit $LASTEXITCODE)"; exit $LASTEXITCODE }
}

Invoke-Step "ruff format" { ruff format --check . }
Invoke-Step "ruff lint"   { ruff check . }
Invoke-Step "mypy"        { mypy --strict src tests }
Invoke-Step "pytest"      { python -m pytest }
Write-Host "gate green"

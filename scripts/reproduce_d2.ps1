param([string]$Python = 'python', [switch]$Full)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& $Python -m venv .venv-d2-repro
if ($LASTEXITCODE) { throw 'venv failed' }
$py = Join-Path (Get-Location) '.venv-d2-repro/Scripts/python.exe'
& $py -m pip install --no-index --find-links dist/wheelhouse dist/causalverse_simulation-0.2.0-py3-none-any.whl pytest==9.2.0
if ($LASTEXITCODE) { throw 'offline install failed' }
& $py -m pytest tests -q
if ($LASTEXITCODE) { throw 'unit tests failed' }
if ($Full) {
    if (Test-Path artifacts/d2/results.json) { throw 'Archive existing artifacts/d2 first; validation must not overwrite prior evidence' }
    & $py scripts/validate_d2.py
    if ($LASTEXITCODE) { throw 'integration failed' }
    & $py scripts/verify_artifacts_d2.py
    if ($LASTEXITCODE) { throw 'artifact verification failed' }
}

$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw 'Build frontend first: cd frontend; npm ci; npm run build' }
$env:PYTHONPATH=(Resolve-Path src).Path
$env:PYTHONUTF8='1'
& '.research/venv-tep/Scripts/python.exe' -m causalverse.dashboard.server

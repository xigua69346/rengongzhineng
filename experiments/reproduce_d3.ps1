param([string]$Python='python')
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (Test-Path artifacts/d3/dataset/split_plan.json) { throw 'Archive artifacts/d3 before a full reproduction; do not overwrite evidence' }
$env:PYTHONPATH=(Resolve-Path src).Path
& $Python experiments/run_dataset.py --freeze
if ($LASTEXITCODE) { throw 'freeze failed' }
& $Python experiments/run_dataset.py
if ($LASTEXITCODE) { throw 'generation failed' }
& $Python experiments/verify_dataset.py
if ($LASTEXITCODE) { throw 'data integrity failed' }
& $Python experiments/run_detection.py
if ($LASTEXITCODE) { throw 'detection failed' }
& $Python -m pytest tests -q
if ($LASTEXITCODE) { throw 'tests failed' }

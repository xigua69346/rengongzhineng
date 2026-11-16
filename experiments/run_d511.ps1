$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath 'artifacts/d5_1_1') {
    throw 'D5.1.1 results exist. Archive them before a fresh reproduction; no results will be overwritten.'
}
$env:PYTHONPATH = (Resolve-Path 'src').Path
$env:PYTHONUTF8 = '1'
$d511Python = Join-Path (Get-Location) '.research/venv-tep/Scripts/python.exe'
function Invoke-D511Python {
    param([string[]]$Arguments)
    & $d511Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "D5.1.1 command failed: $Arguments" }
}
Invoke-D511Python -Arguments @('experiments/d511_data.py','--pilot')
Invoke-D511Python -Arguments @('experiments/d511_data.py','--freeze')
Invoke-D511Python -Arguments @('experiments/d511_data.py')
Invoke-D511Python -Arguments @('experiments/d511_analysis.py')
Invoke-D511Python -Arguments @('experiments/d511_support_audit.py')
Invoke-D511Python -Arguments @('-m','pytest','tests','-q','--junitxml=artifacts/d5_1_1/tests.xml')
Invoke-D511Python -Arguments @('experiments/d511_reports.py')
Invoke-D511Python -Arguments @('experiments/d511_finalize.py')

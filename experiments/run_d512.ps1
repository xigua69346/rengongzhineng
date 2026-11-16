$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath 'artifacts/d5_1_2') {
    throw 'D5.1.2 results already exist; archive separately before fresh reproduction.'
}
$env:PYTHONPATH = (Resolve-Path 'src').Path
$env:PYTHONUTF8 = '1'
$d512Python = Join-Path (Get-Location) '.research/venv-tep/Scripts/python.exe'
function Invoke-D512Python {
    param([string[]]$Arguments)
    & $d512Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "D5.1.2 command failed: $Arguments" }
}
Invoke-D512Python -Arguments @('experiments/d512_mechanisms.py','--freeze')
Invoke-D512Python -Arguments @('experiments/d512_mechanisms.py')
Invoke-D512Python -Arguments @('-m','pytest','tests','-q','--junitxml=artifacts/d5_1_2/tests.xml')
Invoke-D512Python -Arguments @('experiments/d512_reports.py')

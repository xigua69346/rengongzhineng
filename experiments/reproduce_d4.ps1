param([string]$Python='python')
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if(Test-Path artifacts/d4/protocol.json){throw 'Archive artifacts/d4 first; preserve all D2/D3 artifacts'}
$env:PYTHONPATH=(Resolve-Path src).Path
foreach($script in @('d4_freeze','d4_pair_simulation','d4_models','d4_discovery','d4_interventions','d4_paired_diagnosis')){
    & $Python "experiments/$script.py"
    if($LASTEXITCODE){throw "$script failed; outputs retained"}
}
& $Python -m pytest tests -q | Tee-Object -FilePath artifacts/d4/test_report.txt
if($LASTEXITCODE){throw 'Tests failed'}
& $Python experiments/d4_audit.py
if($LASTEXITCODE){throw 'Audit failed'}
& $Python experiments/d4_reports.py
if($LASTEXITCODE){throw 'Reports failed'}

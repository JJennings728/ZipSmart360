# Prepare a reproducible, synthetic-only Power BI Desktop demo without modifying existing databases.
# PowerShell 5.1+ on Windows. Does not publish, deploy, merge or use customer data.
[CmdletBinding()]
param(
    [switch]$OpenDesktop
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
$project = Split-Path -Parent $PSScriptRoot
$pbip = Join-Path $project 'powerbi\AeroCIE-Underwriting.pbip'
if (-not (Test-Path -LiteralPath $pbip -PathType Leaf)) { throw "Missing PBIP project: $pbip" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python is not on PATH.' }
$run = Join-Path ([System.IO.Path]::GetTempPath()) ('AeroCIE-Demo-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $run -ErrorAction Stop | Out-Null
$database = Join-Path $run 'synthetic.db'
$export = Join-Path $run 'powerbi-import'
function Invoke-CheckedPython {
    param([string[]]$Arguments)
    & python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed (exit $LASTEXITCODE): $($Arguments -join ' ')" }
}
Push-Location $project
try {
    Invoke-CheckedPython -Arguments @('-m', 'src.aerocie.underwriting_pipeline', '--db', $database, '--export-dir', $export)
    Invoke-CheckedPython -Arguments @('-m', 'src.aerocie.export_reconciliation', '--export-dir', $export)
    Invoke-CheckedPython -Arguments @('scripts/validate_powerbi.py')
    Invoke-CheckedPython -Arguments @('-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests/test_aerocie_knowledge_graph.py', 'tests/test_aerocie_underwriting_pipeline.py', 'tests/test_aerocie_export_reconciliation.py', 'tests/test_aerocie_powerbi_dashboard.py')
    $cases = @(Import-Csv -LiteralPath (Join-Path $export 'v_submission_triage.csv'))
    if ($cases.Count -ne 7 -or (@($cases.submission_id | Select-Object -Unique)).Count -ne 7) {
        throw 'Seven unique synthetic submissions were not exported.'
    }
    Write-Host ''
    Write-Host 'SYNTHETIC DEMO PREPARATION: PASS (does NOT verify Desktop rendering)' -ForegroundColor Green
    Write-Host ('Dataset: ' + $export)
    Write-Host ('PBIP: ' + $pbip)
    Write-Host ('Desktop parameter AeroCIEDataFolder: ' + ($export.TrimEnd('\') + '\'))
    Write-Host 'Open PBIP in Power BI Desktop, set AeroCIEDataFolder, refresh, inspect all four pages and capture the acceptance evidence.'
    Write-Host 'DO NOT publish or share as an FAA-approved, actuarially calibrated, or production release.'
    if ($OpenDesktop) { Invoke-Item -LiteralPath $pbip }
}
finally { Pop-Location }

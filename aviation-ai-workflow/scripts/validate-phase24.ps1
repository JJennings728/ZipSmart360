[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [switch]$OpenDemo
)
$ErrorActionPreference = 'Stop'
$Project = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path -LiteralPath $Python)) { throw "Python executable not found: $Python" }
$OutBase = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SRP-AeroCIE'
New-Item -ItemType Directory -Path $OutBase -Force | Out-Null
$Out = Join-Path $OutBase ('Underwriting-Validation-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Out -ErrorAction Stop | Out-Null
$Db = Join-Path $Out 'aerocie_synthetic_underwriting.db'
$Csv = Join-Path $Out 'powerbi-import'
$Html = Join-Path $Out 'AeroCIE-Underwriting-Preview.html'
$Eval = Join-Path $Out 'pilot-scorecard.json'
$Economics = Join-Path $Out 'pilot-economics.json'
$OldByteCode = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $Project
try {
    Write-Host 'RUNNING UNDERWRITING + PILOT TESTS' -ForegroundColor Cyan
    & $Python -m pytest -p no:cacheprovider -q tests/test_aerocie_underwriting_pipeline.py tests/test_aerocie_pilot_commercial.py
    if ($LASTEXITCODE -ne 0) { throw 'Underwriting tests failed' }
    Write-Host 'BUILDING SYNTHETIC UNDERWRITING DATABASE' -ForegroundColor Cyan
    & $Python -m src.aerocie.underwriting_pipeline --db $Db --export-dir $Csv
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic database creation failed' }
    & $Python -m src.aerocie.underwriting_preview --db $Db --out-html $Html
    if ($LASTEXITCODE -ne 0) { throw 'HTML dashboard creation failed' }
    & $Python -m src.aerocie.pilot_evaluation --input 'sample-data/phase24/synthetic-pilot-evaluation.json' --out $Eval
    if ($LASTEXITCODE -ne 0) { throw 'Evaluation failed' }
    & $Python -m src.aerocie.pilot_economics --assumptions 'sample-data/phase24/pilot-economics-assumptions.json' --out $Economics
    if ($LASTEXITCODE -ne 0) { throw 'Economics failed' }
    if ($OpenDemo) { Start-Process -FilePath $Html }
    Write-Host "Validation artifacts: $Out" -ForegroundColor Green
    Write-Host 'Synthetic advisory research only; verify Power BI calculations in Desktop.'
} finally {
    Pop-Location
    $env:PYTHONDONTWRITEBYTECODE = $OldByteCode
}

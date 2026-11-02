[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [switch]$OpenDemo
)
$ErrorActionPreference = "Stop"
$Project = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path -LiteralPath $Python)) { throw "Python executable not found: $Python" }
if (-not (Test-Path -LiteralPath (Join-Path $Project "src\aerocie\pilot_report.py"))) {
    throw "AeroCIE Phase 21 module not found"
}
$Work = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "SRP-AeroCIE"
New-Item -ItemType Directory -Force -Path $Work | Out-Null
$Out = Join-Path $Work ("Phase21-Preview-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Out -ErrorAction Stop | Out-Null
$Html = Join-Path $Out "AeroCIE-Pilot-Research-Preview.html"
$ExistingBytecode = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONDONTWRITEBYTECODE = "1"
Push-Location $Project
try {
    Write-Host "RUNNING PHASE 21 REPORT TESTS" -ForegroundColor Cyan
    & $Python -m pytest -p no:cacheprovider tests/test_aerocie_pilot_report.py -q
    if ($LASTEXITCODE -ne 0) { throw "Phase 21 focused tests failed" }
    Write-Host "RUNNING AEROCIE REGRESSION TESTS" -ForegroundColor Cyan
    & $Python -m pytest -p no:cacheprovider tests/test_aerocie_*.py tests/test_fr_*.py -q
    if ($LASTEXITCODE -ne 0) { throw "AeroCIE regression tests failed" }
    Write-Host "GENERATING SYNTHETIC PILOT REPORT" -ForegroundColor Cyan
    & $Python -m src.aerocie.pilot_report `
        --intake "sample-data\phase20\intake.json" `
        --packet "sample-data\phase20\packet.json" `
        --out-html $Html
    if ($LASTEXITCODE -ne 0) { throw "Phase 21 report generation failed" }
    if ($OpenDemo) { Start-Process -FilePath $Html }
    Write-Host "PHASE 21 OUTPUT: $Html" -ForegroundColor Green
    Write-Host "INTERNAL SYNTHETIC DEMONSTRATION - NO CUSTOMER RELEASE"
}
finally {
    Pop-Location
    $env:PYTHONDONTWRITEBYTECODE = $ExistingBytecode
}

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [int]$Port = 8092,
    [switch]$SkipTests
)
$ErrorActionPreference = "Stop"
$Project = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path -LiteralPath $Python)) { throw "Python executable not found: $Python" }
if ($Port -lt 1024 -or $Port -gt 65535) { throw "Port must be between 1024 and 65535" }
$Previous = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONDONTWRITEBYTECODE = "1"
Push-Location $Project
try {
    if (-not $SkipTests) {
        Write-Host "RUNNING PHASE 22 WORKBENCH TESTS" -ForegroundColor Cyan
        & $Python -m pytest -p no:cacheprovider tests/test_aerocie_workbench.py -q
        if ($LASTEXITCODE -ne 0) { throw "Phase 22 workbench tests failed" }
        Write-Host "RUNNING AEROCIE REGRESSION" -ForegroundColor Cyan
        & $Python -m pytest -p no:cacheprovider tests/test_aerocie_*.py tests/test_fr_*.py -q
        if ($LASTEXITCODE -ne 0) { throw "AeroCIE regression failed" }
    }
    $Url = "http://127.0.0.1:$Port/"
    Write-Host "WORKBENCH: $Url" -ForegroundColor Green
    Write-Host "Open the URL in your browser; use Ctrl+C to stop the local server."
    & $Python -m src.aerocie.workbench --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Local workbench server failed" }
}
finally {
    Pop-Location
    $env:PYTHONDONTWRITEBYTECODE = $Previous
}

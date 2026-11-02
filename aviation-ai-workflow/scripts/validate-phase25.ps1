[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [switch]$OpenDemo
)
$ErrorActionPreference = 'Stop'
$Project = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path -LiteralPath $Python)) { throw "Python not found: $Python" }
$OutputRoot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SRP-AeroCIE'
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$Run = Join-Path $OutputRoot ('Underwriting-Quality-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $Run -ErrorAction Stop | Out-Null
$Db = Join-Path $Run 'synthetic-underwriting.db'
$Csv = Join-Path $Run 'powerbi-import'
$Html = Join-Path $Run 'AeroCIE-Underwriting-Quality.html'
$Audit = Join-Path $Run 'Underwriting-Quality-Audit.json'
$ExistingBytecode = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $Project
try {
    $Tests = @(Get-ChildItem (Join-Path $Project 'tests') -Filter 'test_aerocie_*.py' -File | ForEach-Object { $_.FullName })
    $Tests += @(Get-ChildItem (Join-Path $Project 'tests') -Filter 'test_fr_*.py' -File | ForEach-Object { $_.FullName })
    if ($Tests.Count -eq 0) { throw 'No tests found' }
    Write-Host "RUNNING $($Tests.Count) AEROCIE REGRESSION MODULES" -ForegroundColor Cyan
    & $Python -m pytest -p no:cacheprovider -q @Tests
    if ($LASTEXITCODE -ne 0) { throw 'AeroCIE regression tests failed' }
    Write-Host 'CREATING LOCAL SYNTHETIC DATABASE' -ForegroundColor Cyan
    & $Python -m src.aerocie.underwriting_pipeline --db $Db --export-dir $Csv
    if ($LASTEXITCODE -ne 0) { throw 'Synthetic database and Power BI export failed' }
    & $Python -m src.aerocie.underwriting_quality --db $Db --out $Audit
    if ($LASTEXITCODE -ne 0) { throw 'Quality audit failed' }
    & $Python -m src.aerocie.underwriting_preview --db $Db --out-html $Html
    if ($LASTEXITCODE -ne 0) { throw 'Dashboard generation failed' }
    if ($OpenDemo) { Start-Process -FilePath $Html }
    Write-Host "AeroCIE quality validation: $Run" -ForegroundColor Green
    Write-Host 'Data mode: synthetic. Underwriting authority: human review required.'
}
finally {
    Pop-Location
    $env:PYTHONDONTWRITEBYTECODE = $ExistingBytecode
}

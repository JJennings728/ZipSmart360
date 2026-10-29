[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$Python)
$ErrorActionPreference = 'Stop'
$Project = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path -LiteralPath $Python)) { throw "Python executable missing: $Python" }
$OutRoot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SRP-AeroCIE'
New-Item -Path $OutRoot -ItemType Directory -Force | Out-Null
$Out = Join-Path $OutRoot ('Phase23-Assurance-' + [guid]::NewGuid().ToString('N') + '.json')
Push-Location $Project
try {
    & $Python -m pytest -p no:cacheprovider tests/test_aerocie_model_assurance.py -q
    if ($LASTEXITCODE -ne 0) { throw 'Model assurance focused tests failed' }
    & $Python -m pytest -p no:cacheprovider tests/test_aerocie_*.py tests/test_fr_*.py -q
    if ($LASTEXITCODE -ne 0) { throw 'AeroCIE regression suite failed' }
    & $Python -m src.aerocie.model_assurance --input 'sample-data/phase23/synthetic-model-eval.json' --out-json $Out
    if ($LASTEXITCODE -ne 0) { throw 'Model assurance output generation failed' }
    Write-Host "Model assurance report: $Out" -ForegroundColor Green
} finally { Pop-Location }

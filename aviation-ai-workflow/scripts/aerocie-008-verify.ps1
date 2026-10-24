# AeroCIE-008 | Non-destructive local verification.
# Execute only after the draft PR has been reviewed and merged.
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $project
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python launcher py is not installed. Install Python 3.11+ first.'
    }
    Write-Host 'AeroCIE-008 | Run offline unit tests'
    py -m unittest tests.test_aerocie_obligation_register -v
    if ($LASTEXITCODE -ne 0) { throw 'AeroCIE-008 tests failed; no DB initialized.' }
    Write-Host 'AeroCIE-008 | Initialize local research database'
    py -m src.aerocie.obligation_register init
    if ($LASTEXITCODE -ne 0) { throw 'AeroCIE-008 local init failed.' }
    Write-Host 'AeroCIE-008 | Display candidates (no compliance determinations)'
    py -m src.aerocie.obligation_register list
    if ($LASTEXITCODE -ne 0) { throw 'AeroCIE-008 list failed.' }
    Write-Host 'Complete | Local-only research prototype | No credentials used'
} finally {
    Pop-Location
}

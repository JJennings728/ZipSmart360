[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$OutputRoot = (Join-Path ([Environment]::GetFolderPath("MyDocuments")) "SRP-AeroCIE"),
    [switch]$OpenDemo
)
$ErrorActionPreference = "Stop"
$Project = Split-Path $PSScriptRoot -Parent
# Use only bundled source and synthetic fixtures; never copy .env or existing research databases.
$Run = Join-Path $OutputRoot ("Phase20-Validation-" + [guid]::NewGuid().ToString("N"))
$Work = Join-Path $Run "aviation-ai-workflow"
New-Item -ItemType Directory -Path $Work -Force | Out-Null
foreach ($Folder in @("src", "tests", "sample-data")) {
    $Source = Join-Path $Project $Folder
    foreach ($File in (Get-ChildItem -LiteralPath $Source -Recurse -File)) {
        if ($File.FullName -match '[\\/]__pycache__[\\/]') { continue }
        if ($File.Extension -notin @(".py", ".json", ".txt")) { continue }
        $Relative = $File.FullName.Substring($Source.Length).TrimStart([char[]]"\/")
        $Target = Join-Path (Join-Path $Work $Folder) $Relative
        New-Item -ItemType Directory -Path (Split-Path $Target -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $File.FullName -Destination $Target -ErrorAction Stop
    }
}
$PythonCommand = (Get-Command $Python -ErrorAction Stop).Source
Push-Location $Work
try {
    & $PythonCommand -m pytest tests/test_aerocie_demo_brief.py -q 2>&1 | Tee-Object (Join-Path $Run "phase19-tests.txt")
    if ($LASTEXITCODE -ne 0) { throw "Phase 19 failed; see phase19-tests.txt. Verify requirements are installed." }
    & $PythonCommand -m pytest -q 2>&1 | Tee-Object (Join-Path $Run "regression-tests.txt")
    if ($LASTEXITCODE -ne 0) { throw "Regression tests failed; see regression-tests.txt." }
    $Demo = Join-Path $Run "phase19-demo.html"
    & $PythonCommand -m src.aerocie.demo_brief --packet sample-data/phase20/packet.json --out-html $Demo
    if ($LASTEXITCODE -ne 0) { throw "Phase 19 demo generation failed." }
    $Report = Join-Path $Run "sample-deliverable"
    & $PythonCommand -m src.aerocie.customer_report --intake sample-data/phase20/intake.json --packet sample-data/phase20/packet.json --out-dir $Report
    if ($LASTEXITCODE -ne 0) { throw "Phase 20 sample generation failed." }
    if ($OpenDemo) {
        Start-Process -FilePath $Demo
        Start-Process -FilePath (Join-Path $Report "report.html")
    }
    Write-Host "Validation output: $Run"
    Write-Host "Synthetic fixtures only. Browser rendering still requires visual verification."
} finally {
    Pop-Location
}

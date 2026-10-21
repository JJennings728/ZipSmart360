# AeroCIE daily FAA monitor runner. Local-only; requires Python 3.11+.
# Runs using the existing project directory and preserves local SQLite history.
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logFolder = Join-Path $projectRoot 'build\aerocie\logs'
New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
$logPath = Join-Path $logFolder ("monitor-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
Set-Location $projectRoot
try {
    & py -m src.aerocie.monitor --lookback-days 7 --limit 500 --report-dir 'build/aerocie/reports' *>&1 | Out-File -FilePath $logPath -Encoding UTF8
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Error "AeroCIE monitoring requires attention (exit $exitCode). See: $logPath"
        exit $exitCode
    }
    Write-Output "AeroCIE completed. Run log: $logPath"
    exit 0
} catch {
    ($_ | Out-String) | Out-File -FilePath $logPath -Encoding UTF8 -Append
    Write-Error "AeroCIE monitoring failed. See: $logPath"
    exit 1
}

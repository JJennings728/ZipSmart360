<#
.SYNOPSIS
  Open a clean, isolated AeroCIE Phase 28 branded report in Power BI Desktop.
.DESCRIPTION
  Makes a detached Git worktree under LOCALAPPDATA and configures only its
  local AeroCIEDataFolder expression. Never modifies the user's working
  repository, prior worktrees, SQLite databases, or CSV exports.
  The PBIR must still be visually verified by an operator in Desktop.
.EXAMPLE
  .\open_phase28_windows_preview.ps1 -Repository 'C:\...\ZipSmart360' -CsvFolder 'C:\...\powerbi-import'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Repository,
    [Parameter(Mandatory=$true)][string]$CsvFolder,
    [string]$RemoteBranch = 'origin/feature/aerocie-028-branded-four-page-pbir',
    [switch]$NoLaunch
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not (Test-Path -LiteralPath $Repository -PathType Container)) {
    throw "Repository does not exist: $Repository"
}
$CsvFolder = (Resolve-Path -LiteralPath $CsvFolder -ErrorAction Stop).ProviderPath
$Expected = @(
    'v_submission_features',
    'v_submission_triage',
    'v_mro_latest',
    'v_mro_model_metrics',
    'source_registry',
    'v_severity_scenarios',
    'submission_quality'
)
foreach ($t in $Expected) {
    $csv = Join-Path $CsvFolder ($t + '.csv')
    if (-not (Test-Path -LiteralPath $csv -PathType Leaf)) {
        throw "Missing CSV; nothing was changed: $csv"
    }
}
$GitStatus = & git -C $Repository rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0) { throw 'Unable to access Git repository.' }
$Base = Join-Path $env:LOCALAPPDATA 'SRP-AeroCIE'
if (-not (Test-Path -LiteralPath $Base)) {
    New-Item -ItemType Directory -Path $Base -Force | Out-Null
}
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Preview = Join-Path $Base ("PBIR-Preview-" + $Stamp)
if (Test-Path -LiteralPath $Preview) { throw "Preview path already exists: $Preview" }

Write-Host 'Fetching the branded AeroCIE draft branch without changing the current checkout...' -ForegroundColor Cyan
& git -C $Repository fetch origin feature/aerocie-028-branded-four-page-pbir
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed; original files unchanged.' }
& git -C $Repository worktree add --detach $Preview $RemoteBranch
if ($LASTEXITCODE -ne 0) { throw 'Creating the separate preview failed.' }

$ProjectRoot = Join-Path $Preview 'aviation-ai-workflow\powerbi'
$Report = Join-Path $ProjectRoot 'AeroCIE-Underwriting.Report'
$Definition = Join-Path $Report 'definition'
$Model = Join-Path $ProjectRoot 'AeroCIE-Underwriting.SemanticModel'
$PBIP = Join-Path $ProjectRoot 'AeroCIE-Underwriting.pbip'
$PagesFile = Join-Path $Definition 'pages\pages.json'
$VersionFile = Join-Path $Definition 'version.json'
$ExpressionFile = Join-Path $Model 'definition\expressions.tmdl'

foreach ($f in @($PBIP, $PagesFile, $VersionFile, $ExpressionFile)) {
    if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { throw "Required report file missing: $f" }
}
$Pages = Get-Content -LiteralPath $PagesFile -Raw | ConvertFrom-Json
$Ver = Get-Content -LiteralPath $VersionFile -Raw | ConvertFrom-Json
$ExpectPages = @('Overview','RiskAnalysis','MROSeverity','EvidenceQuality')
if ($Ver.version -ne '2.0.0') { throw "Unexpected report definition version: $($Ver.version)" }
if (($Pages.pageOrder -join ',') -ne ($ExpectPages -join ',')) {
    throw "Expected four PBIR report pages, found: $($Pages.pageOrder -join ',')"
}
$Count = 0
foreach ($p in $ExpectPages) {
    $PgFile = Join-Path $Definition ("pages\" + $p + "\page.json")
    if (-not (Test-Path -LiteralPath $PgFile)) { throw "Missing report page: $p" }
    $VisFolder = Join-Path $Definition ("pages\" + $p + "\visuals")
    $Count += @(Get-ChildItem -LiteralPath $VisFolder -Recurse -Filter visual.json -File).Count
}
if ($Count -lt 50) { throw "Expected at least 50 report visuals, found $Count" }
$reportMetadata = Get-Content -LiteralPath (Join-Path $Definition 'report.json') -Raw | ConvertFrom-Json
if ($reportMetadata.themeCollection.customTheme.reportVersionAtImport -isnot [string]) {
    throw 'PBIR theme metadata is still invalid.'
}

# Change the parameter only in this clean preview; leave GitHub, previous
# worktrees, and the user's local original entirely unchanged.
$Expression = [System.IO.File]::ReadAllText($ExpressionFile)
$Current = 'expression AeroCIEDataFolder = "C:\AeroCIE\Export\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
$NewPath = $CsvFolder.TrimEnd([char]'\') + '\'
$NewLine = 'expression AeroCIEDataFolder = "' + $NewPath + '" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
if (-not $Expression.Contains($Current)) {
    throw 'The expected editable parameter expression was not found. No existing files were overwritten.'
}
$Expression = $Expression.Replace($Current, $NewLine)
$UTF8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ExpressionFile, $Expression, $UTF8)

Write-Host ('Verified report pages: ' + ($Pages.pageOrder -join ', ')) -ForegroundColor Green
Write-Host "Verified PBIR visual definitions: $Count" -ForegroundColor Green
Write-Host "Verified data: $($Expected.Count) CSV files" -ForegroundColor Green
Write-Host "Isolated report path: $PBIP" -ForegroundColor Cyan
Write-Host 'Note: PBIR source validation does not verify actual Desktop rendering.' -ForegroundColor Yellow
if (-not $NoLaunch) {
    Start-Process -FilePath $PBIP
}

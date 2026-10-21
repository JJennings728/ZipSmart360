# Opt-in: run this ONCE in a normal PowerShell session to register the task.
# No task is registered merely by downloading this file or merging the PR.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')]
    [string]$At
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$dailyRunner = Join-Path $PSScriptRoot 'aerocie-run-daily.ps1'
if (!(Test-Path $dailyRunner)) { throw "Runner missing: $dailyRunner" }
if (!(Get-Command py -ErrorAction SilentlyContinue)) { throw 'Python launcher py.exe unavailable.' }
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $dailyRunner + '"') -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($At, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture))
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName 'SRP AeroCIE FAA Monitor' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Local FAA public-source metadata check and review artifacts, no customer data.' -Force | Out-Null
Write-Output "Registered: SRP AeroCIE FAA Monitor at $At local computer time (runs only while signed in)."
Write-Output 'You can view or disable it in Windows Task Scheduler. No emails or external notifications are sent.'

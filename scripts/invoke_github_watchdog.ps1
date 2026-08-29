[CmdletBinding()]
param(
    [string]$Repository = "ai-studying-man/DAPA_NEWS",
    [int]$MaxAttempts = 360,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogDirectory = Join-Path $RepoRoot "logs"
$LogPath = Join-Path $LogDirectory "github_watchdog.log"
$KoreaTimeZone = [TimeZoneInfo]::FindSystemTimeZoneById("Korea Standard Time")

if (-not (Test-Path -LiteralPath $LogDirectory)) {
    New-Item -ItemType Directory -Path $LogDirectory | Out-Null
}

function Write-WatchdogLog {
    param([Parameter(Mandatory)][string]$Message)

    $nowKst = [TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $KoreaTimeZone)
    $line = "{0:yyyy-MM-dd HH:mm:ss} KST {1}" -f $nowKst, $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding utf8
    Write-Output $line
}

if ($MaxAttempts -lt 1) {
    throw "MaxAttempts must be at least 1."
}

$nowKst = [TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $KoreaTimeZone)
$windowStart = $nowKst.Date.AddHours(5).AddMinutes(40)
$windowEnd = $nowKst.Date.AddHours(12)
if (-not $Force -and ($nowKst -lt $windowStart -or $nowKst -ge $windowEnd)) {
    Write-WatchdogLog "Outside the 05:40-12:00 watchdog window; no dispatch requested."
    exit 0
}

$ghCommand = Get-Command gh.exe -ErrorAction SilentlyContinue
if ($null -eq $ghCommand) {
    Write-WatchdogLog "GitHub CLI was not found on PATH."
    exit 1
}

$requestedDate = $nowKst.ToString("yyyy-MM-dd")
if ($DryRun) {
    Write-WatchdogLog "Dry run: would request dapa-morning-brief-watchdog for $requestedDate."
    exit 0
}

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    Write-WatchdogLog "Dispatch attempt $attempt of $MaxAttempts for $requestedDate."
    $dispatchOutput = & $ghCommand.Source api --method POST `
        "repos/$Repository/dispatches" `
        -f "event_type=dapa-morning-brief-watchdog" `
        -F "client_payload[requested_date]=$requestedDate" `
        -F "client_payload[retry_count]=0" `
        -F "client_payload[source]=windows-task-scheduler" 2>&1
    $dispatchExitCode = $LASTEXITCODE

    if ($dispatchOutput) {
        $dispatchOutput | ForEach-Object {
            Write-WatchdogLog "GitHub CLI: $_"
        }
    }
    if ($dispatchExitCode -eq 0) {
        Write-WatchdogLog "GitHub accepted the watchdog dispatch request."
        exit 0
    }
    if ($attempt -lt $MaxAttempts) {
        Write-WatchdogLog "Dispatch failed with exit code $dispatchExitCode; retrying in 60 seconds."
        Start-Sleep -Seconds 60
    }
}

Write-WatchdogLog "All $MaxAttempts watchdog dispatch attempts failed."
exit 1

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
$FailureLogPath = Join-Path $LogDirectory "github_watchdog_failures.jsonl"
$KoreaTimeZone = [TimeZoneInfo]::FindSystemTimeZoneById("Korea Standard Time")

if (-not (Test-Path -LiteralPath $LogDirectory)) {
    New-Item -ItemType Directory -Path $LogDirectory | Out-Null
}

function Write-WatchdogLog {
    param([Parameter(Mandatory)][string]$Message)

    $nowKst = [TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $KoreaTimeZone)
    $line = "{0:yyyy-MM-dd HH:mm:ss} KST {1}" -f $nowKst, $Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding utf8
    Write-Host $line
}

function Write-FailureRecord {
    param(
        [Parameter(Mandatory)][string]$Phase,
        [Parameter(Mandatory)][int]$Attempt,
        [AllowNull()][object]$RunId,
        [AllowNull()][string]$Conclusion,
        [AllowNull()][object]$Details
    )

    $record = [ordered]@{
        recorded_at_utc = [DateTime]::UtcNow.ToString("o")
        phase = $Phase
        attempt = $Attempt
        repository = $Repository
        run_id = $RunId
        conclusion = $Conclusion
        details = $Details
    }
    $record | ConvertTo-Json -Compress -Depth 10 |
        Add-Content -LiteralPath $FailureLogPath -Encoding utf8
}

function Invoke-GhApiJson {
    param([Parameter(Mandatory)][string]$Uri)

    $apiOutput = & $ghCommand.Source api $Uri 2>&1
    $apiExitCode = $LASTEXITCODE
    if ($apiExitCode -ne 0) {
        Write-WatchdogLog "GitHub API request failed with exit code $apiExitCode for $Uri."
        return $null
    }
    try {
        return (($apiOutput -join "`n") | ConvertFrom-Json)
    }
    catch {
        Write-WatchdogLog "GitHub API returned invalid JSON for $Uri."
        return $null
    }
}

function Get-FailedRunDetails {
    param(
        [Parameter(Mandatory)][long]$RunId,
        [Parameter(Mandatory)][string]$RunUrl
    )

    $jobsResponse = Invoke-GhApiJson "repos/$Repository/actions/runs/$RunId/jobs?per_page=100"
    $failedJobs = @()
    if ($null -ne $jobsResponse) {
        foreach ($job in @($jobsResponse.jobs)) {
            $failedSteps = @(
                foreach ($step in @($job.steps)) {
                    if ($step.conclusion -in @(
                        "failure", "cancelled", "timed_out", "action_required", "stale"
                    )) {
                        [ordered]@{
                            number = $step.number
                            name = $step.name
                            conclusion = $step.conclusion
                            started_at = $step.started_at
                            completed_at = $step.completed_at
                        }
                    }
                }
            )
            if ($job.conclusion -notin @("success", "skipped", $null) -or $failedSteps.Count -gt 0) {
                $failedJobs += [ordered]@{
                    id = $job.id
                    name = $job.name
                    conclusion = $job.conclusion
                    started_at = $job.started_at
                    completed_at = $job.completed_at
                    failed_steps = $failedSteps
                }
            }
        }
    }
    return [ordered]@{
        run_url = $RunUrl
        failed_jobs = $failedJobs
    }
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
    $dispatchStartedUtc = [DateTime]::UtcNow
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
        $runId = $null
        $runUrl = $null
        for ($poll = 1; $poll -le 7 -and $null -eq $runId; $poll++) {
            if ($poll -gt 1) {
                Start-Sleep -Seconds 10
            }
            $runsResponse = Invoke-GhApiJson `
                "repos/$Repository/actions/workflows/dapa-morning-brief.yml/runs?event=repository_dispatch&per_page=20"
            if ($null -eq $runsResponse) {
                continue
            }
            foreach ($candidate in @($runsResponse.workflow_runs)) {
                $createdUtc = [DateTimeOffset]::Parse([string]$candidate.created_at).UtcDateTime
                if (
                    $candidate.display_title -eq "dapa-morning-brief-watchdog" -and
                    $createdUtc -ge $dispatchStartedUtc.AddSeconds(-5)
                ) {
                    $runId = [long]$candidate.id
                    $runUrl = [string]$candidate.html_url
                    break
                }
            }
        }

        if ($null -eq $runId) {
            $message = "Dispatch was accepted but no matching Actions run was created within 60 seconds."
            Write-WatchdogLog $message
            Write-FailureRecord `
                -Phase "run-not-created" `
                -Attempt $attempt `
                -RunId $null `
                -Conclusion "missing" `
                -Details @{ message = $message }
            continue
        }

        Write-WatchdogLog "Tracking Actions run $runId at $runUrl."
        $runCompleted = $false
        for ($runPoll = 1; $runPoll -le 1440; $runPoll++) {
            $runResponse = Invoke-GhApiJson "repos/$Repository/actions/runs/$runId"
            if ($null -eq $runResponse) {
                Start-Sleep -Seconds 15
                continue
            }
            if ($runResponse.status -ne "completed") {
                Start-Sleep -Seconds 15
                continue
            }

            $runCompleted = $true
            $conclusion = [string]$runResponse.conclusion
            if ($conclusion -eq "success") {
                Write-WatchdogLog "Actions run $runId completed successfully."
                exit 0
            }

            $failureDetails = Get-FailedRunDetails -RunId $runId -RunUrl $runUrl
            Write-FailureRecord `
                -Phase "run-completed" `
                -Attempt $attempt `
                -RunId $runId `
                -Conclusion $conclusion `
                -Details $failureDetails
            Write-WatchdogLog "Actions run $runId completed with conclusion '$conclusion'; retrying in 60 seconds."
            break
        }

        if (-not $runCompleted) {
            $message = "Actions run $runId did not complete within the six-hour monitoring limit."
            Write-WatchdogLog $message
            Write-FailureRecord `
                -Phase "run-monitor-timeout" `
                -Attempt $attempt `
                -RunId $runId `
                -Conclusion "timed_out" `
                -Details @{ run_url = $runUrl; message = $message }
        }
        if ($attempt -lt $MaxAttempts) {
            Start-Sleep -Seconds 60
        }
        continue
    }
    Write-FailureRecord `
        -Phase "dispatch-failed" `
        -Attempt $attempt `
        -RunId $null `
        -Conclusion "failure" `
        -Details @{ exit_code = $dispatchExitCode }
    if ($attempt -lt $MaxAttempts) {
        Write-WatchdogLog "Dispatch failed with exit code $dispatchExitCode; retrying in 60 seconds."
        Start-Sleep -Seconds 60
    }
}

Write-WatchdogLog "All $MaxAttempts watchdog dispatch attempts failed."
exit 1

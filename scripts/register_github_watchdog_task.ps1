[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$TaskName = "DAPA Morning Brief Watchdog"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$WatchdogScript = Join-Path $PSScriptRoot "invoke_github_watchdog.ps1"
$PowerShellPath = Join-Path $env:SystemRoot `
    "System32\WindowsPowerShell\v1.0\powershell.exe"
$DailyStartTime = "05:45"

if (-not (Test-Path -LiteralPath $WatchdogScript)) {
    throw "Watchdog script not found: $WatchdogScript"
}

$actionArguments = @(
    "-NoLogo"
    "-NoProfile"
    "-NonInteractive"
    "-ExecutionPolicy Bypass"
    "-File `"$WatchdogScript`""
) -join " "
$action = New-ScheduledTaskAction `
    -Execute $PowerShellPath `
    -Argument $actionArguments `
    -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -Daily -At $DailyStartTime
$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 360 `
    -ExecutionTimeLimit (New-TimeSpan -Hours 6) `
    -MultipleInstances IgnoreNew
$settings.WakeToRun = $true
$settings.StartWhenAvailable = $true
$principal = New-ScheduledTaskPrincipal `
    -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel Limited

if (-not $PSCmdlet.ShouldProcess($TaskName, "Register daily 05:45 KST watchdog")) {
    return
}
Register-ScheduledTask `
    -TaskName $TaskName `
    -Description "Wake this PC and request the DAPA production workflow at 05:45 KST." `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

$registeredTask = Get-ScheduledTask -TaskName $TaskName
$registeredInfo = $registeredTask | Get-ScheduledTaskInfo
[pscustomobject]@{
    TaskName = $registeredTask.TaskName
    State = $registeredTask.State
    NextRunTime = $registeredInfo.NextRunTime
    WakeToRun = $registeredTask.Settings.WakeToRun
    StartWhenAvailable = $registeredTask.Settings.StartWhenAvailable
    RestartCount = $registeredTask.Settings.RestartCount
    RestartInterval = $registeredTask.Settings.RestartInterval
    Execute = $registeredTask.Actions.Execute
    Arguments = $registeredTask.Actions.Arguments
} | Format-List

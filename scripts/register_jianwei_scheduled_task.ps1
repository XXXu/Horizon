param(
    [string]$TaskName = "Jianwei Export Upload",
    [string[]]$Times = @("09:00", "18:00"),
    [int]$Hours = 24,
    [int]$Limit = 100
)

$ErrorActionPreference = "Stop"

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RunnerScript = Join-Path $PSScriptRoot "run_jianwei_export_upload.ps1"
$PowerShellPath = (Get-Command powershell.exe).Source

if (-not (Test-Path $RunnerScript -PathType Leaf)) {
    throw "Task runner script not found: $RunnerScript"
}

$actionArguments = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$RunnerScript`"",
    "-Hours",
    $Hours,
    "-Limit",
    $Limit
) -join " "

$action = New-ScheduledTaskAction `
    -Execute $PowerShellPath `
    -Argument $actionArguments `
    -WorkingDirectory $RootDir

$triggers = foreach ($time in $Times) {
    New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($time, "HH:mm", $null))
}

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -WakeToRun

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Principal $principal `
    -Settings $settings `
    -Description "Run Horizon Jianwei export, upload, and server import on schedule." `
    -Force | Out-Null

Write-Host "Created or updated Windows scheduled task: $TaskName"
Write-Host "Run times: $($Times -join ', ')"
Write-Host "Start when available: enabled"
Write-Host "Wake to run: enabled"
Write-Host "Runner script: $RunnerScript"
Write-Host "Log file: $(Join-Path $RootDir 'logs\jianwei_export_upload.log')"

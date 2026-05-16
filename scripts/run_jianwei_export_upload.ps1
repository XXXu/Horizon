param(
    [int]$Hours = 24,
    [int]$Limit = 100,
    [Nullable[double]]$MinScore = $null,
    [switch]$SkipRemoteImport
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $RootDir "logs"
$LogPath = Join-Path $LogDir "jianwei_export_upload.log"
$ExportScript = Join-Path $PSScriptRoot "export_and_upload_jianwei.ps1"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    $ExportScript,
    "-Hours",
    $Hours,
    "-Limit",
    $Limit
)

if ($null -ne $MinScore) {
    $arguments += @("-MinScore", $MinScore)
}

if ($SkipRemoteImport) {
    $arguments += "-SkipRemoteImport"
}

$startedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogPath -Encoding utf8 -Value ""
Add-Content -Path $LogPath -Encoding utf8 -Value "===== Jianwei export upload started: $startedAt ====="

Push-Location $RootDir
try {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & powershell.exe @arguments 2>&1 | ForEach-Object {
            $line = $_.ToString()
            Write-Host $line
            Add-Content -Path $LogPath -Encoding utf8 -Value $line
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $finishedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogPath -Encoding utf8 -Value "===== Jianwei export upload finished: $finishedAt, exit code: $exitCode ====="

    if ($exitCode -ne 0) {
        throw "Jianwei export upload failed, exit code: $exitCode. Log: $LogPath"
    }
}
finally {
    Pop-Location
}

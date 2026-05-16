param(
    [string]$PersonaSlug = "indie-maker",
    [int]$Hours = 24,
    [int]$Limit = 100,
    [Nullable[double]]$MinScore = $null,
    [string]$RemoteHost = $null,
    [string]$RemoteArtifactsRoot = $null,
    [string]$RemoteWebDir = $null,
    [string]$PythonPath = $(Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"),
    [switch]$SkipRemoteImport
)

$ErrorActionPreference = "Stop"

function Read-DotEnv {
    param([string]$Path)

    $values = @{}
    if (-not (Test-Path $Path -PathType Leaf)) {
        return $values
    }

    foreach ($line in Get-Content -Path $Path -Encoding utf8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        if ($trimmed.StartsWith("export ")) {
            $trimmed = $trimmed.Substring(7).TrimStart()
        }

        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -ne 2) {
            continue
        }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (-not $key) {
            continue
        }

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $values[$key] = $value
    }

    return $values
}

function Get-ConfigValue {
    param(
        [hashtable]$DotEnvValues,
        [string]$ParameterName,
        [string]$ParameterValue,
        [string]$EnvName,
        [string]$DefaultValue = $null
    )

    if ($PSBoundParameters.ContainsKey("ParameterValue") -and $ParameterValue) {
        return $ParameterValue
    }
    if ($script:BoundParameters.ContainsKey($ParameterName) -and $ParameterValue) {
        return $ParameterValue
    }
    $envValue = [Environment]::GetEnvironmentVariable($EnvName, "Process")
    if ($envValue) {
        return $envValue
    }
    if ($DotEnvValues.ContainsKey($EnvName) -and $DotEnvValues[$EnvName]) {
        return $DotEnvValues[$EnvName]
    }
    return $DefaultValue
}

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonPath = (Resolve-Path $PythonPath).Path
$script:BoundParameters = $PSBoundParameters
$DotEnvValues = Read-DotEnv (Join-Path $RootDir ".env")

foreach ($key in $DotEnvValues.Keys) {
    if (-not [Environment]::GetEnvironmentVariable($key, "Process")) {
        [Environment]::SetEnvironmentVariable($key, $DotEnvValues[$key], "Process")
    }
}

$RemoteHost = Get-ConfigValue `
    -DotEnvValues $DotEnvValues `
    -ParameterName "RemoteHost" `
    -ParameterValue $RemoteHost `
    -EnvName "JIANWEI_REMOTE_HOST"
$RemoteArtifactsRoot = Get-ConfigValue `
    -DotEnvValues $DotEnvValues `
    -ParameterName "RemoteArtifactsRoot" `
    -ParameterValue $RemoteArtifactsRoot `
    -EnvName "JIANWEI_REMOTE_ARTIFACTS_ROOT" `
    -DefaultValue "/root/workspace/vertical_ai_news/artifacts"
$RemoteWebDir = Get-ConfigValue `
    -DotEnvValues $DotEnvValues `
    -ParameterName "RemoteWebDir" `
    -ParameterValue $RemoteWebDir `
    -EnvName "JIANWEI_REMOTE_WEB_DIR" `
    -DefaultValue "/root/workspace/vertical_ai_news/jianwei_web"

if (-not $RemoteHost) {
    throw "请通过 -RemoteHost、环境变量 JIANWEI_REMOTE_HOST 或 .env 中的 JIANWEI_REMOTE_HOST 指定服务器，例如：root@129.204.144.110"
}

if ([string]::IsNullOrWhiteSpace($PersonaSlug)) {
    throw "PersonaSlug 不能为空"
}

if ([string]::IsNullOrWhiteSpace($RemoteArtifactsRoot) -or $RemoteArtifactsRoot -eq "/") {
    throw "RemoteArtifactsRoot 不能为空，也不能是根目录 /"
}

if ([string]::IsNullOrWhiteSpace($RemoteWebDir) -or $RemoteWebDir -eq "/") {
    throw "RemoteWebDir 不能为空，也不能是根目录 /"
}

$RemoteArtifactsRoot = $RemoteArtifactsRoot.TrimEnd("/")
$RemoteWebDir = $RemoteWebDir.TrimEnd("/")

Push-Location $RootDir
try {
    $ArtifactDate = (& $PythonPath -c "from src.integrations.jianwei import artifact_date_for_display_timezone; print(artifact_date_for_display_timezone())").Trim()
    $ArtifactDir = Join-Path $RootDir "data\jianwei_artifacts\$ArtifactDate\$PersonaSlug"
    if (Test-Path $ArtifactDir) {
        Write-Host "清理本地旧 artifact 目录：$ArtifactDir"
        Remove-Item -LiteralPath $ArtifactDir -Recurse -Force
    }

    $exportArgs = @(
        "-m", "src.integrations.jianwei",
        "--persona-slug", $PersonaSlug,
        "--hours", $Hours,
        "--limit", $Limit
    )

    if ($null -ne $MinScore) {
        $exportArgs += @("--min-score", $MinScore)
    }

    Write-Host "开始导出见微 artifacts..."
    & $PythonPath @exportArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Horizon 导出失败，退出码：$LASTEXITCODE"
    }

    if (-not (Test-Path $ArtifactDir -PathType Container)) {
        throw "未找到 artifact 目录：$ArtifactDir"
    }

    $ArtifactFiles = @(Get-ChildItem -Path $ArtifactDir -Filter "*.json" -File)
    if ($ArtifactFiles.Count -eq 0) {
        throw "artifact 目录中没有 JSON 文件：$ArtifactDir"
    }

    $RemoteDateDir = "$RemoteArtifactsRoot/$ArtifactDate"
    Write-Host "准备上传 $($ArtifactFiles.Count) 个 JSON 到 ${RemoteHost}:$RemoteDateDir/$PersonaSlug"
    ssh $RemoteHost "rm -rf '$RemoteDateDir/$PersonaSlug' && mkdir -p '$RemoteDateDir'"
    if ($LASTEXITCODE -ne 0) {
        throw "服务器目录创建失败，退出码：$LASTEXITCODE"
    }

    scp -r $ArtifactDir "${RemoteHost}:$RemoteDateDir/"
    if ($LASTEXITCODE -ne 0) {
        throw "artifact 上传失败，退出码：$LASTEXITCODE"
    }

    if (-not $SkipRemoteImport) {
        Write-Host "开始在服务器导入 artifact..."
        ssh $RemoteHost "cd '$RemoteWebDir' && bash ./bin/import_uploaded_artifacts.sh '$ArtifactDate'"
        if ($LASTEXITCODE -ne 0) {
            throw "服务器导入失败，退出码：$LASTEXITCODE"
        }
    }
    else {
        Write-Host "已跳过服务器导入。服务器手动导入命令："
        Write-Host "cd $RemoteWebDir && bash ./bin/import_uploaded_artifacts.sh $ArtifactDate"
    }

    Write-Host "完成：本地导出、上传、服务器导入流程已结束。"
}
finally {
    Pop-Location
}

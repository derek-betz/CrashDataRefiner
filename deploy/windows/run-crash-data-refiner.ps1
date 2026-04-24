param(
    [string]$AppRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$EnvFile = "C:\ProgramData\CrashDataRefiner\config\app.env",
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8081,
    [string]$LogPath = "C:\ProgramData\CrashDataRefiner\logs\crash-data-refiner.log"
)

$ErrorActionPreference = "Stop"

function Import-EnvFile {
    param([string]$PathValue)

    if (-not (Test-Path -LiteralPath $PathValue)) {
        Write-Host "Env file not found, continuing with existing environment: ${PathValue}"
        return
    }

    Get-Content -LiteralPath $PathValue | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        $pair = $line -split "=", 2
        if ($pair.Count -ne 2) {
            throw "Invalid env line in ${PathValue}: $line"
        }
        [Environment]::SetEnvironmentVariable($pair[0].Trim(), $pair[1].Trim(), "Process")
    }
}

function Set-DefaultEnv {
    param(
        [string]$Name,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($Name, "Process"))) {
        [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
    }
}

$pythonExe = Join-Path $AppRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

Import-EnvFile -PathValue $EnvFile

$outputsRoot = "C:\ProgramData\CrashDataRefiner\outputs\web_runs"
$previewRoot = "C:\ProgramData\CrashDataRefiner\outputs\preview"
$logsRoot = Split-Path -Parent $LogPath

foreach ($pathValue in @($outputsRoot, $previewRoot, $logsRoot)) {
    if (-not (Test-Path -LiteralPath $pathValue)) {
        New-Item -ItemType Directory -Path $pathValue -Force | Out-Null
    }
}

Set-DefaultEnv -Name "APP_ENV" -Value "production"
Set-DefaultEnv -Name "CDR_HOST" -Value $BindHost
Set-DefaultEnv -Name "CDR_PORT" -Value "$Port"
Set-DefaultEnv -Name "CDR_THREADS" -Value "4"
Set-DefaultEnv -Name "CDR_OUTPUT_ROOT" -Value $outputsRoot
Set-DefaultEnv -Name "CDR_PREVIEW_ROOT" -Value $previewRoot
Set-DefaultEnv -Name "CDR_MAX_UPLOAD_BYTES" -Value "209715200"

$effectiveHost = [Environment]::GetEnvironmentVariable("CDR_HOST", "Process")
$effectivePort = [Environment]::GetEnvironmentVariable("CDR_PORT", "Process")

Write-Host "Starting CrashDataRefiner"
Write-Host "AppRoot: $AppRoot"
Write-Host "EnvFile: $EnvFile"
Write-Host "Host: $effectiveHost"
Write-Host "Port: $effectivePort"
Write-Host "LogPath: $LogPath"
Write-Host ""

if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$previousErrorActionPreference = $ErrorActionPreference
try {
    $ErrorActionPreference = "Continue"
    & $pythonExe -m crash_data_refiner.webapp --host $effectiveHost --port $effectivePort 2>&1 | Tee-Object -FilePath $LogPath -Append
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
}

exit $LASTEXITCODE

[CmdletBinding()]
param(
    [int]$Port = 8081,
    [string]$BindHost = "127.0.0.1",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$browserHost = $BindHost
if ($browserHost -in @("0.0.0.0", "::")) {
    $browserHost = "127.0.0.1"
}

Push-Location $repoRoot
try {
    $env:PYTHONPATH = $repoRoot.Path

    Write-Host "Crash Data Refiner web app"
    Write-Host "URL: http://$browserHost`:$Port"
    Write-Host "Suggested sample files:"
    Write-Host "  tests\\refiner_inputs\\2101166_Crash-Data.xlsx"
    Write-Host "  tests\\refiner_inputs\\2101166_Relevance Boundary.kmz"

    if ($OpenBrowser) {
        Start-Process "http://$browserHost`:$Port"
    }

    python -m crash_data_refiner.webapp --host $BindHost --port $Port
} finally {
    Pop-Location
}

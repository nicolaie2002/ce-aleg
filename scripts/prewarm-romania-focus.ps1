param(
    [string]$BackendDir = "",
    [string]$Country = "romania",
    [string]$Categories = "",
    [int]$LimitPerCategory = 30,
    [int]$PageSize = 30,
    [switch]$Apply,
    [switch]$WorldFallback
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

if (-not $BackendDir) {
    $BackendDir = Join-Path $root "backend"
}

if (-not (Test-Path $BackendDir)) {
    throw "Backend directory not found: $BackendDir"
}

$venvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
$env:PYTHONIOENCODING = "utf-8"

$selectedCountry = if ($WorldFallback) { "world" } else { $Country }
$argsList = @(
    "prewarm_openfoodfacts_catalog.py",
    "--preset", "romania_focus",
    "--country", $selectedCountry,
    "--limit-per-category", $LimitPerCategory,
    "--page-size", $PageSize
)

if ($Categories) {
    $argsList += @("--categories", $Categories)
}

if (-not $Apply) {
    $argsList += "--dry-run"
    Write-Host "Dry run only. Re-run with -Apply to persist these products."
}

Push-Location $BackendDir
try {
    & $python @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "Romania focus Open Food Facts prewarm failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}

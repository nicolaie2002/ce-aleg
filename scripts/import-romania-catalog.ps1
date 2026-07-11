param(
    [string]$BackendDir = "",
    [string]$Country = "romania",
    [int]$Limit = 5000,
    [int]$MaxScan = 800000,
    [int]$SkipRows = 0,
    [switch]$RequireBarcode,
    [switch]$DryRun,
    [switch]$NoRecategorize,
    [int]$RecategorizeLimit = 1000,
    [switch]$ApplyRecategorize
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

$importArgs = @(
    "import_openfoodfacts_export.py",
    "--country", $Country,
    "--limit", $Limit,
    "--max-scan", $MaxScan,
    "--progress-every", 5000
)

if ($SkipRows -gt 0) {
    $importArgs += @("--skip-rows", $SkipRows)
}

if (-not $RequireBarcode) {
    $importArgs += "--allow-no-barcode"
}

if ($DryRun) {
    $importArgs += "--dry-run"
}

Push-Location $BackendDir
try {
    Write-Host "Importing Open Food Facts catalog slice..."
    & $python @importArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Open Food Facts import failed with exit code $LASTEXITCODE."
    }

    if (-not $NoRecategorize) {
        $recategorizeArgs = @("recategorize_catalog.py", "--limit", $RecategorizeLimit)

        if ($ApplyRecategorize -and -not $DryRun) {
            $recategorizeArgs += "--apply"
        } else {
            Write-Host "Recategorization will run as dry-run. Add -ApplyRecategorize to persist changes."
        }

        Write-Host "Checking catalog categories..."
        & $python @recategorizeArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Catalog recategorization failed with exit code $LASTEXITCODE."
        }
    }
} finally {
    Pop-Location
}

param(
    [switch]$Smoke,
    [switch]$IncludeExternal,
    [string]$FrontendUrl = "http://localhost:3000",
    [string]$BackendUrl = "http://127.0.0.1:5001"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$python = Join-Path $backendDir "venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "Checking backend syntax..."
Push-Location $backendDir
& $python -m py_compile app.py models.py database.py
Pop-Location

Write-Host "Scanning source files for exposed production secrets..."
$secretPattern = "(sk_(live|test)_[A-Za-z0-9]{20,}|whsec_[A-Za-z0-9]{20,}|xkeysib-[A-Za-z0-9_-]{20,}|sb_secret_[A-Za-z0-9_-]{20,})"
$secretMatches = & rg `
    --hidden `
    --line-number `
    --glob "!backend/.env" `
    --glob "!**/node_modules/**" `
    --glob "!**/venv/**" `
    --glob "!**/libretranslate-venv/**" `
    --glob "!frontend/.next/**" `
    $secretPattern `
    $root 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host $secretMatches
    throw "Potential production secret found in source-controlled files."
}

Write-Host "Checking frontend lint..."
Push-Location $frontendDir
Write-Host "Checking frontend routes..."
& (Join-Path $PSScriptRoot "verify-routes.ps1") -FrontendDir $frontendDir

& npm.cmd run lint

Write-Host "Building frontend..."
& npm.cmd run build
Pop-Location

if ($Smoke) {
    Write-Host "Running smoke tests..."
    $smokeArgs = @{
        FrontendUrl = $FrontendUrl
        BackendUrl = $BackendUrl
    }

    if ($IncludeExternal) {
        $smokeArgs.IncludeExternal = $true
    }

    & (Join-Path $PSScriptRoot "smoke-test.ps1") @smokeArgs

    if ($LASTEXITCODE -ne 0) {
        throw "Smoke tests failed."
    }
}

Write-Host "Project verification completed." -ForegroundColor Green

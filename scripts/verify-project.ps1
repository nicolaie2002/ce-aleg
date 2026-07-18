param(
    [switch]$Smoke,
    [switch]$E2E,
    [switch]$IncludeExternal,
    [string]$FrontendUrl = "http://localhost:3000",
    [string]$BackendUrl = "http://127.0.0.1:5001"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$python = Join-Path $backendDir "venv\Scripts\python.exe"

function Assert-CommandSucceeded([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path $python)) {
    $python = "python"
}

Write-Host "Checking backend syntax, lint, and tests..."
Push-Location $backendDir
& $python -m py_compile app.py app_factory.py catalog_quality.py config.py models.py database.py restore_supabase_storage.py time_utils.py
Assert-CommandSucceeded "Backend compilation"
& $python -m compileall -q routes
Assert-CommandSucceeded "Backend route compilation"
& $python -m ruff check . --select E9,F63,F7,F82
Assert-CommandSucceeded "Backend lint"
& $python -m pytest tests -W error::DeprecationWarning --cov=app --cov=api_docs --cov=routes --cov-fail-under=70 -q
Assert-CommandSucceeded "Backend tests"
Pop-Location

Write-Host "Checking representative backend p95 latency..."
& $python (Join-Path $PSScriptRoot "benchmark-backend.py") --iterations 60 --threshold-ms 500
Assert-CommandSucceeded "Backend latency benchmark"

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
Assert-CommandSucceeded "Frontend lint"
& npm.cmd run typecheck
Assert-CommandSucceeded "Frontend typecheck"
& npm.cmd run test:ci -- --runInBand --passWithNoTests
Assert-CommandSucceeded "Frontend tests"

Write-Host "Building frontend..."
& npm.cmd run build
Assert-CommandSucceeded "Frontend build"
Pop-Location

if ($E2E) {
    Write-Host "Running full-stack Playwright tests..."
    Push-Location $frontendDir
    $previousFullStack = $env:PLAYWRIGHT_FULL_STACK
    $previousCi = $env:CI
    try {
        $env:PLAYWRIGHT_FULL_STACK = "true"
        $env:CI = "true"
        & npm.cmd run test:e2e
        Assert-CommandSucceeded "Full-stack E2E tests"
    }
    finally {
        $env:PLAYWRIGHT_FULL_STACK = $previousFullStack
        $env:CI = $previousCi
        Pop-Location
    }
}

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

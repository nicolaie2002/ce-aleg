param(
    [int]$FrontendPort = 3000,
    [int]$BackendPort = 5001,
    [switch]$SkipTranslate,
    [switch]$LocalDatabase,
    [switch]$Visible
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$backendPython = Join-Path $backendDir "venv\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
    $backendPython = "python"
}

function Test-ListeningPort {
    param([int]$Port)

    try {
        return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

function Start-LocalProcess {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $windowStyle = if ($Visible) { "Normal" } else { "Hidden" }

    $process = Start-Process powershell.exe `
        -WorkingDirectory $WorkingDirectory `
        -WindowStyle $windowStyle `
        -PassThru `
        -ArgumentList @(
            "-NoExit",
            "-ExecutionPolicy", "Bypass",
            "-Command", $Command
        )

    Write-Host "$Name started. PID $($process.Id)"
}

if (Test-ListeningPort $BackendPort) {
    Write-Host "Backend port $BackendPort is already in use."
} else {
    $databaseOverride = if ($LocalDatabase) {
        "`$env:DATABASE_URL=' '; "
    } else {
        ""
    }
    $backendCommand = "$databaseOverride`$env:PORT='$BackendPort'; & '$backendPython' app.py"
    Start-LocalProcess "Backend" $backendDir $backendCommand
}

if (-not $SkipTranslate) {
    if (Test-ListeningPort 5002) {
        Write-Host "LibreTranslate port 5002 is already in use."
    } else {
        $translateCommand = ".\run_libretranslate.cmd"
        Start-LocalProcess "LibreTranslate" $backendDir $translateCommand
    }
}

if (Test-ListeningPort $FrontendPort) {
    Write-Host "Frontend port $FrontendPort is already in use."
} else {
    $frontendCommand = "`$env:BACKEND_URL='http://127.0.0.1:$BackendPort'; npm.cmd run dev -- -p $FrontendPort"
    Start-LocalProcess "Frontend" $frontendDir $frontendCommand
}

Write-Host ""
Write-Host "Frontend: http://localhost:$FrontendPort"
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
if ($LocalDatabase) {
    Write-Host "Database: local SQLite (backend/instance/cealeg.db)"
} else {
    Write-Host "Database: DATABASE_URL from backend/.env"
}
Write-Host "Run smoke tests with:"
Write-Host "powershell -ExecutionPolicy Bypass -File scripts\smoke-test.ps1 -FrontendUrl http://localhost:$FrontendPort -BackendUrl http://127.0.0.1:$BackendPort"

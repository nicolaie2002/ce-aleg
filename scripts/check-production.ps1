param(
    [string]$BackendUrl = "https://cealeg-api.onrender.com",
    [string]$FrontendUrl = ""
)

$ErrorActionPreference = "Stop"
$backend = $BackendUrl.TrimEnd("/")

function Invoke-Check {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    try {
        & $Action
        Write-Host "[OK] $Name" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] $Name - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed = $true
    }
}

$failed = $false

Invoke-Check "Backend health" {
    $response = Invoke-WebRequest "$backend/health" -UseBasicParsing -TimeoutSec 90
    if ($response.StatusCode -ne 200) {
        throw "HTTP $($response.StatusCode)"
    }
}

Invoke-Check "Anonymous readiness is blocked" {
    try {
        Invoke-WebRequest "$backend/readiness" -UseBasicParsing -TimeoutSec 90 | Out-Null
        throw "Endpoint returned success without authentication."
    } catch {
        if (-not $_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 401) {
            throw
        }
    }
}

Invoke-Check "Anonymous account access is blocked" {
    try {
        Invoke-WebRequest "$backend/auth/me" -UseBasicParsing -TimeoutSec 90 | Out-Null
        throw "Endpoint returned success without authentication."
    } catch {
        if (-not $_.Exception.Response -or [int]$_.Exception.Response.StatusCode -ne 401) {
            throw
        }
    }
}

if ($FrontendUrl) {
    $frontend = $FrontendUrl.TrimEnd("/")

    Invoke-Check "Frontend home" {
        $response = Invoke-WebRequest $frontend -UseBasicParsing -TimeoutSec 90
        if ($response.StatusCode -ne 200) {
            throw "HTTP $($response.StatusCode)"
        }
    }

    Invoke-Check "Frontend backend proxy" {
        $response = Invoke-WebRequest "$frontend/api/backend/health" -UseBasicParsing -TimeoutSec 90
        if ($response.StatusCode -ne 200) {
            throw "HTTP $($response.StatusCode)"
        }
    }
}

if ($failed) {
    exit 1
}

Write-Host "Production checks passed." -ForegroundColor Green

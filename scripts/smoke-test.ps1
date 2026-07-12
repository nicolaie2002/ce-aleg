param(
    [string]$FrontendUrl = "http://localhost:3000",
    [string]$BackendUrl = "http://127.0.0.1:5001",
    [switch]$SkipAuthWrites,
    [switch]$IncludeExternal
)

$ErrorActionPreference = "Stop"

$results = New-Object System.Collections.Generic.List[object]
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$testEmail = "smoke+$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())@cealeg.test"
$testPassword = "SmokeTest1!"

function Add-Result {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail = ""
    )

    $results.Add([pscustomobject]@{
        Name = $Name
        Passed = $Passed
        Detail = $Detail
    }) | Out-Null
}

function Get-ErrorBody {
    param($ErrorRecord)

    $response = $ErrorRecord.Exception.Response

    if (-not $response) {
        return $ErrorRecord.Exception.Message
    }

    try {
        $stream = $response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        return $reader.ReadToEnd()
    } catch {
        return $ErrorRecord.Exception.Message
    }
}

function Test-Status {
    param(
        [string]$Name,
        [string]$Url,
        [int[]]$Expected = @(200)
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 25
        $status = [int]$response.StatusCode
        Add-Result $Name ($Expected -contains $status) "HTTP $status"
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Add-Result $Name ($Expected -contains $status) "HTTP $status $(Get-ErrorBody $_)"
    }
}

function Test-Header {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Header,
        [string]$ExpectedPattern,
        [int[]]$ExpectedStatus = @(200)
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 25
        $status = [int]$response.StatusCode
        $value = [string]$response.Headers[$Header]
        Add-Result $Name (($ExpectedStatus -contains $status) -and ($value -match $ExpectedPattern)) "HTTP $status $Header=$value"
    } catch {
        $response = $_.Exception.Response
        $status = if ($response) { [int]$response.StatusCode } else { 0 }
        $value = if ($response) { [string]$response.Headers[$Header] } else { "" }
        Add-Result $Name (($ExpectedStatus -contains $status) -and ($value -match $ExpectedPattern)) "HTTP $status $Header=$value"
    }
}

function Test-CrossSiteMutationBlocked {
    param([string]$Url)

    try {
        Invoke-WebRequest `
            -Uri $Url `
            -Method POST `
            -UseBasicParsing `
            -ContentType "application/json" `
            -Headers @{
                Origin = "https://attacker.example"
                "Sec-Fetch-Site" = "cross-site"
                "Sec-Fetch-Mode" = "cors"
            } `
            -Body '{"password":"ExamplePassword1!"}' `
            -TimeoutSec 25 | Out-Null
        Add-Result "Cross-site mutation is blocked" $false "Request unexpectedly succeeded."
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Add-Result "Cross-site mutation is blocked" ($status -eq 403) "HTTP $status"
    }
}

function Invoke-Json {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        $Body = $null,
        $WebSession = $null,
        [int[]]$Expected = @(200)
    )

    $parameters = @{
        Uri = $Url
        Method = $Method
        UseBasicParsing = $true
        TimeoutSec = 30
    }

    if ($WebSession) {
        $parameters.WebSession = $WebSession
    }

    if ($null -ne $Body) {
        $parameters.ContentType = "application/json"
        $parameters.Body = ($Body | ConvertTo-Json -Depth 12)
    }

    try {
        $response = Invoke-WebRequest @parameters
        $status = [int]$response.StatusCode
        $passed = $Expected -contains $status
        Add-Result $Name $passed "HTTP $status"

        if ($response.Content) {
            return $response.Content | ConvertFrom-Json
        }

        return $null
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
        Add-Result $Name ($Expected -contains $status) "HTTP $status $(Get-ErrorBody $_)"
        return $null
    }
}

Write-Host "Smoke test frontend: $FrontendUrl"
Write-Host "Smoke test backend:  $BackendUrl"

Test-Status "Backend health" "$BackendUrl/health"
Test-Header "Backend sends request IDs" "$BackendUrl/health" "X-Request-ID" ".+"
Test-Header "Backend blocks framing" "$BackendUrl/health" "X-Frame-Options" "^DENY$"
Test-Header "Backend sends CSP" "$BackendUrl/health" "Content-Security-Policy" "default-src 'none'"
Test-Status "Backend readiness is admin-only" "$BackendUrl/readiness" @(401)
Test-Status "Frontend home" "$FrontendUrl/"
Test-Header "Frontend sends CSP" "$FrontendUrl/" "Content-Security-Policy" "default-src 'self'"
Test-Header "Frontend blocks framing" "$FrontendUrl/" "X-Frame-Options" "^DENY$"
Test-Status "Frontend login" "$FrontendUrl/login"
Test-Status "Frontend register" "$FrontendUrl/register"
Test-Status "Frontend forgot password" "$FrontendUrl/forgot-password"
Test-Status "Frontend delete account" "$FrontendUrl/delete-account"
Test-Status "Frontend pricing" "$FrontendUrl/pricing"
Test-Status "Frontend privacy" "$FrontendUrl/privacy"
Test-Status "Frontend terms" "$FrontendUrl/terms"
Test-Status "Frontend scan page" "$FrontendUrl/barcode-scan"
Test-Status "Frontend live assistant page" "$FrontendUrl/live-assistant"
Test-Status "Frontend cron route is secret-only" "$FrontendUrl/api/cron/maintenance" @(401)
Test-Status "Unauthenticated billing is blocked" "$BackendUrl/billing/status" @(401)
Test-Header "Sensitive responses disable cache" "$BackendUrl/auth/me" "Cache-Control" "no-store" @(401)
Test-CrossSiteMutationBlocked "$BackendUrl/auth/password-strength"
Invoke-Json "Unauthenticated email test is blocked" "POST" "$BackendUrl/admin/email-test" @{} $null @(401) | Out-Null
Invoke-Json "Unauthenticated mission digest is blocked" "POST" "$BackendUrl/admin/missions/digest" @{} $null @(401) | Out-Null
Test-Status "Unauthenticated admin product search is blocked" "$BackendUrl/admin/products/search" @(401)
Invoke-Json "Unauthenticated admin product update is blocked" "PATCH" "$BackendUrl/admin/products/1" @{} $null @(401) | Out-Null
Invoke-Json "Unauthenticated internal cron is blocked" "POST" "$BackendUrl/internal/cron/maintenance" @{} $null @(401) | Out-Null
Invoke-Json "Unauthenticated delete request is blocked" "POST" "$BackendUrl/account/delete/request" @{} $null @(401) | Out-Null
Invoke-Json "Invalid account delete token is rejected" "POST" "$BackendUrl/account/delete/confirm" @{ token = "invalid-token" } $null @(400) | Out-Null

$strength = Invoke-Json "Password strength endpoint" "POST" "$BackendUrl/auth/password-strength" @{ password = "abc" }
if ($strength) {
    Add-Result "Weak password rejected by policy" (-not $strength.isValid) "isValid=$($strength.isValid)"
}

if (-not $SkipAuthWrites) {
    $registered = Invoke-Json "Register smoke user" "POST" "$BackendUrl/register" @{
        name = "Smoke Test"
        email = $testEmail
        password = $testPassword
        ageConfirmed = $true
        acceptedTerms = $true
    } $session @(201, 409)

    if ($registered -and $registered.user) {
        Add-Result "Register returned user" $true "userId=$($registered.user.id)"
    }

    $me = Invoke-Json "Authenticated /auth/me" "GET" "$BackendUrl/auth/me" $null $session
    if ($me -and $me.user) {
        Add-Result "Auth cookie works" $true "email=$($me.user.email)"
    }

    Invoke-Json "Billing status with auth" "GET" "$BackendUrl/billing/status" $null $session | Out-Null
    Invoke-Json "Forgot password generic response" "POST" "$BackendUrl/forgot-password" @{ email = $testEmail } | Out-Null

    $loginSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    Invoke-Json "Login smoke user" "POST" "$BackendUrl/login" @{
        email = $testEmail
        password = $testPassword
    } $loginSession | Out-Null
    Invoke-Json "Login cookie /auth/me" "GET" "$BackendUrl/auth/me" $null $loginSession | Out-Null

    if ($IncludeExternal) {
        $barcode = Invoke-Json "Open Food Facts barcode lookup" "GET" "$BackendUrl/barcode/lookup/3017624010701" $null $session @(200, 404, 502)
        if ($barcode) {
            Add-Result "Barcode lookup returned structured JSON" ($null -ne $barcode.found) "found=$($barcode.found)"
        }
    }
}

$failed = @($results | Where-Object { -not $_.Passed })

Write-Host ""
$results | Format-Table -AutoSize

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "Smoke test failed: $($failed.Count) check(s)." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Smoke test passed: $($results.Count) checks." -ForegroundColor Green

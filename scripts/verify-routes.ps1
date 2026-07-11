param(
    [string]$FrontendDir = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

if (-not $FrontendDir) {
    $FrontendDir = Join-Path $root "frontend"
}

$appDir = Join-Path $FrontendDir "app"
$appDirFull = (Resolve-Path $appDir).Path.TrimEnd("\", "/")
$proxyPath = Join-Path $FrontendDir "proxy.js"
$sitemapPath = Join-Path $appDir "sitemap.js"
$robotsPath = Join-Path $appDir "robots.js"

if (-not (Test-Path $appDir)) {
    throw "Frontend app directory not found: $appDir"
}

function Convert-PageFileToRoute {
    param([System.IO.FileInfo]$File)

    $relative = $File.FullName.Substring($appDirFull.Length).TrimStart("\", "/")
    $relative = $relative.Replace("\", "/")
    $folder = Split-Path $relative -Parent

    if (-not $folder -or $folder -eq ".") {
        return "/"
    }

    return "/" + $folder.Replace("\", "/")
}

$routes = Get-ChildItem -Path $appDir -Recurse -Filter "page.js" |
    ForEach-Object { Convert-PageFileToRoute $_ } |
    Sort-Object -Unique

$requiredPublicPages = @(
    "/",
    "/pricing",
    "/login",
    "/register",
    "/forgot-password",
    "/reset-password",
    "/verify-email",
    "/delete-account",
    "/support",
    "/privacy",
    "/terms",
    "/billing/success",
    "/billing/cancel"
)

$requiredProtectedPages = @(
    "/admin",
    "/alternatives",
    "/barcode-scan",
    "/cart",
    "/dashboard",
    "/favorites",
    "/history",
    "/live-assistant",
    "/missions",
    "/preferences",
    "/result",
    "/scan",
    "/store",
    "/submit-product"
)

$requiredSitemapRoutes = @(
    "",
    "/pricing",
    "/login",
    "/register",
    "/support",
    "/privacy",
    "/terms"
)

$requiredRobotsDisallow = @(
    "/admin",
    "/api",
    "/barcode-scan",
    "/cart",
    "/dashboard",
    "/delete-account",
    "/favorites",
    "/history",
    "/live-assistant",
    "/missions",
    "/preferences",
    "/reset-password",
    "/result",
    "/scan",
    "/store",
    "/submit-product",
    "/verify-email"
)

$missingPages = @(
    $requiredPublicPages + $requiredProtectedPages |
        Where-Object { $routes -notcontains $_ }
)

$proxy = Get-Content -Raw $proxyPath
$missingProxyRoutes = @(
    $requiredProtectedPages |
        Where-Object { $proxy -notmatch [regex]::Escape("$_/:path*") }
)

$sitemap = Get-Content -Raw $sitemapPath
$missingSitemapRoutes = @(
    $requiredSitemapRoutes |
        Where-Object {
            if ($_ -eq "") {
                $sitemap -notmatch '"",'
            } else {
                $sitemap -notmatch [regex]::Escape('"'+$_+'"')
            }
        }
)

$robots = Get-Content -Raw $robotsPath
$missingRobotsRoutes = @(
    $requiredRobotsDisallow |
        Where-Object { $robots -notmatch [regex]::Escape('"'+$_+'"') }
)

Write-Host "Frontend routes found: $($routes.Count)"
$routes | ForEach-Object { Write-Host " - $_" }

if ($missingPages.Count -or $missingProxyRoutes.Count -or $missingSitemapRoutes.Count -or $missingRobotsRoutes.Count) {
    if ($missingPages.Count) {
        Write-Host "Missing page files: $($missingPages -join ', ')" -ForegroundColor Red
    }

    if ($missingProxyRoutes.Count) {
        Write-Host "Protected pages missing from proxy matcher: $($missingProxyRoutes -join ', ')" -ForegroundColor Red
    }

    if ($missingSitemapRoutes.Count) {
        Write-Host "Public sitemap routes missing: $($missingSitemapRoutes -join ', ')" -ForegroundColor Red
    }

    if ($missingRobotsRoutes.Count) {
        Write-Host "Robots disallow routes missing: $($missingRobotsRoutes -join ', ')" -ForegroundColor Red
    }

    throw "Frontend route audit failed."
}

Write-Host "Frontend route audit completed." -ForegroundColor Green

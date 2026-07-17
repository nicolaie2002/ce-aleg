import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5001";
const AUTH_CACHE_TTL_MS = 10_000;
const AUTH_FAILURE_CACHE_TTL_MS = 1_500;
const AUTH_CACHE_MAX_ENTRIES = 250;
const sessionCache = new Map();

function cacheSession(sessionToken, valuePromise, ttl) {
  if (sessionCache.size >= AUTH_CACHE_MAX_ENTRIES) {
    sessionCache.delete(sessionCache.keys().next().value);
  }

  sessionCache.set(sessionToken, {
    expiresAt: Date.now() + ttl,
    valuePromise,
  });
}

async function verifySession(sessionToken, cookieHeader) {
  const cached = sessionCache.get(sessionToken);

  if (cached && cached.expiresAt > Date.now()) {
    return cached.valuePromise;
  }

  if (cached) sessionCache.delete(sessionToken);

  const valuePromise = fetch(`${backendUrl}/auth/me`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  })
    .then(async (response) => {
      if (!response.ok) return null;

      const data = await response.json();
      return data.user || null;
    })
    .catch(() => null);

  cacheSession(sessionToken, valuePromise, AUTH_CACHE_TTL_MS);
  const user = await valuePromise;

  if (!user) {
    cacheSession(sessionToken, Promise.resolve(null), AUTH_FAILURE_CACHE_TTL_MS);
  }

  return user;
}

export async function proxy(request) {
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);
  const sessionToken = request.cookies.get("cealeg_session")?.value;

  if (!sessionToken) {
    return NextResponse.redirect(loginUrl);
  }

  try {
    const user = await verifySession(
      sessionToken,
      request.headers.get("cookie") || ""
    );

    if (!user) {
      return NextResponse.redirect(loginUrl);
    }

    if (request.nextUrl.pathname.startsWith("/admin")) {
      if (!user.isAdmin) {
        return NextResponse.redirect(new URL("/dashboard", request.url));
      }
    }
  } catch {
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/admin/:path*",
    "/alternatives/:path*",
    "/barcode-scan/:path*",
    "/cart/:path*",
    "/dashboard/:path*",
    "/favorites/:path*",
    "/history/:path*",
    "/live-assistant/:path*",
    "/missions/:path*",
    "/preferences/:path*",
    "/result/:path*",
    "/scan/:path*",
    "/store/:path*",
    "/submit-product/:path*",
  ],
};

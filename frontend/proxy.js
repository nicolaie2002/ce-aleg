import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5001";

export async function proxy(request) {
  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", request.nextUrl.pathname);

  try {
    const response = await fetch(`${backendUrl}/auth/me`, {
      headers: {
        cookie: request.headers.get("cookie") || "",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.redirect(loginUrl);
    }

    if (request.nextUrl.pathname.startsWith("/admin")) {
      const data = await response.json();

      if (!data.user?.isAdmin) {
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
    "/preferences/:path*",
    "/result/:path*",
    "/scan/:path*",
    "/store/:path*",
    "/submit-product/:path*",
  ],
};

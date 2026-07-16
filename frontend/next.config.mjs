import { withSentryConfig } from "@sentry/nextjs";

const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5001";
const publicApiUrl = process.env.NEXT_PUBLIC_API_URL || "";
const isProduction = process.env.NODE_ENV === "production";
const sentryAuthToken = process.env.SENTRY_AUTH_TOKEN;

function getHttpOrigin(value) {
  if (!value?.startsWith("http")) return "";

  try {
    return new URL(value).origin;
  } catch {
    return "";
  }
}

const publicApiOrigin = getHttpOrigin(publicApiUrl);
const sentryOrigin = getHttpOrigin(process.env.NEXT_PUBLIC_SENTRY_DSN || "");

const scriptSources = [
  "'self'",
  "'unsafe-inline'",
  "'wasm-unsafe-eval'",
  "https://cdn.jsdelivr.net",
  "https://www.googletagmanager.com",
  ...(isProduction ? [] : ["'unsafe-eval'"]),
].join(" ");
const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  `script-src ${scriptSources}`,
  "style-src 'self' 'unsafe-inline'",
  "font-src 'self' data:",
  [
    "img-src 'self' data: blob:",
    "https://images.openfoodfacts.org",
    "https://images.unsplash.com",
    "https://www.google-analytics.com",
    "https://www.googletagmanager.com",
    "https://*.supabase.co",
  ].join(" "),
  [
    "connect-src 'self' blob:",
    "https://cdn.jsdelivr.net",
    "https://tessdata.projectnaptha.com",
    "https://www.google-analytics.com",
    "https://region1.google-analytics.com",
    "https://www.googletagmanager.com",
    "https://*.supabase.co",
    "https://*.ingest.sentry.io",
    "https://*.ingest.us.sentry.io",
    sentryOrigin,
    publicApiOrigin,
  ].join(" "),
  "media-src 'self' blob:",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  isProduction ? "upgrade-insecure-requests" : "",
]
  .filter(Boolean)
  .join("; ");

const nextConfig = {
  poweredByHeader: false,
  compress: true,
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.openfoodfacts.org",
      },
    ],
  },
  allowedDevOrigins: [
    "192.168.0.199",
    "192.168.0.200",
    "cealeg-frontend-niko.loca.lt",
  ],
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "cealeg.shop" }],
        destination: "https://www.cealeg.shop/:path*",
        permanent: true,
      },
      {
        source: "/:path*",
        has: [{ type: "host", value: "ce-aleg.vercel.app" }],
        destination: "https://www.cealeg.shop/:path*",
        permanent: true,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/brand/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=86400, stale-while-revalidate=604800",
          },
        ],
      },
      {
        source: "/products/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=86400, stale-while-revalidate=604800",
          },
        ],
      },
      {
        source: "/stores/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=86400, stale-while-revalidate=604800",
          },
        ],
      },
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-DNS-Prefetch-Control", value: "off" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(self), microphone=(self), geolocation=()",
          },
          ...(isProduction
            ? [
                {
                  key: "Strict-Transport-Security",
                  value: "max-age=31536000; includeSubDomains",
                },
              ]
            : []),
        ],
      },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: sentryAuthToken,
  silent: !process.env.CI,
  widenClientFileUpload: Boolean(sentryAuthToken),
  sourcemaps: sentryAuthToken
    ? { deleteSourcemapsAfterUpload: true }
    : { disable: true },
  webpack: {
    automaticVercelMonitors: true,
    reactComponentAnnotation: {
      enabled: true,
    },
    treeshake: {
      removeDebugLogging: true,
    },
  },
});

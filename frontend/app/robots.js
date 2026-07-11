const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop").replace(/\/$/, "");

export default function robots() {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
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
        "/verify-email",
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}

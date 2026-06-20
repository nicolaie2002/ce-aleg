const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop").replace(/\/$/, "");

const publicRoutes = [
  "",
  "/pricing",
  "/login",
  "/register",
  "/privacy",
  "/terms",
];

export default function sitemap() {
  const now = new Date();

  return publicRoutes.map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified: now,
    changeFrequency: route === "" ? "weekly" : "monthly",
    priority: route === "" ? 1 : 0.7,
  }));
}

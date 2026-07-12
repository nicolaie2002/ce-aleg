import {
  SEO_ALTERNATIVE_GUIDES,
  SEO_CATEGORIES,
  SEO_PRODUCTS,
  SEO_STORES,
} from "./catalog-romania/seo-data";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop").replace(/\/$/, "");

const publicRoutes = [
  "",
  "/catalog-romania",
  "/catalog-romania/alternative",
  "/catalog-romania/categorii",
  "/catalog-romania/magazine",
  "/catalog-romania/produse",
  "/promovare-gratis",
  "/pricing",
  "/login",
  "/register",
  "/support",
  "/privacy",
  "/terms",
];

const catalogSeoRoutes = [
  ...SEO_ALTERNATIVE_GUIDES.map((guide) => `/catalog-romania/alternative/${guide.slug}`),
  ...SEO_CATEGORIES.map((category) => `/catalog-romania/categorii/${category.slug}`),
  ...SEO_PRODUCTS.map((product) => `/catalog-romania/produse/${product.slug}`),
  ...SEO_STORES.map((store) => `/catalog-romania/magazine/${store.slug}`),
];

export default function sitemap() {
  const now = new Date();

  return [...publicRoutes, ...catalogSeoRoutes].map((route) => ({
    url: `${SITE_URL}${route}`,
    lastModified: now,
    changeFrequency: route === "" || route.startsWith("/catalog-romania") ? "weekly" : "monthly",
    priority:
      route === ""
        ? 1
        : route === "/catalog-romania"
          ? 0.85
          : route.startsWith("/catalog-romania")
            ? 0.78
            : 0.7,
  }));
}

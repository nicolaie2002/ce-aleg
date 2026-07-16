import {
  JsonLd,
  buildBreadcrumbJsonLd,
} from "../seo-components";
import { CATALOG_SEO_SITE_URL, SEO_CATEGORIES } from "../seo-data";
import { CatalogCategoriesContent } from "../CatalogHubContent";

export const metadata = {
  title: "Categorii produse România: scanare și alternative",
  description:
    "Ghid public pe categorii pentru produse din România: lactate, mezeluri, dulciuri, băuturi, conserve, panificație și alte produse scanabile.",
  alternates: {
    canonical: "/catalog-romania/categorii",
  },
  openGraph: {
    title: "Categorii produse România | Ce aleg?",
    description:
      "Alege o categorie, scanează codul de bare și compară produse din aceeași familie.",
    url: "/catalog-romania/categorii",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function CatalogCategoriesPage() {
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Categorii produse România",
    url: `${CATALOG_SEO_SITE_URL}/catalog-romania/categorii`,
    description:
      "Categorii publice pentru scanare produse, comparare etichete și completarea catalogului Ce aleg?.",
    mainEntity: SEO_CATEGORIES.map((category) => ({
      "@type": "Thing",
      name: category.name,
      url: `${CATALOG_SEO_SITE_URL}/catalog-romania/categorii/${category.slug}`,
    })),
  };

  return (
    <>
      <JsonLd
        data={buildBreadcrumbJsonLd([
          { name: "Acasă", href: "/" },
          { name: "Catalog România", href: "/catalog-romania" },
          { name: "Categorii", href: "/catalog-romania/categorii" },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogCategoriesContent categories={SEO_CATEGORIES} />
    </>
  );
}

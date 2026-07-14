import {
  JsonLd,
  buildBreadcrumbJsonLd,
} from "../seo-components";
import { CATALOG_SEO_SITE_URL, SEO_STORES } from "../seo-data";
import { CatalogStoresContent } from "./StoreCatalogContent";

export const metadata = {
  title: "Magazine România: Lidl, Kaufland, Carrefour, Mega, Profi, Penny",
  description:
    "Pagini publice pentru magazine din România unde poți scana produse, compara alternative și contribui la catalogul Ce aleg?.",
  alternates: {
    canonical: "/catalog-romania/magazine",
  },
  openGraph: {
    title: "Magazine România | Catalog Ce aleg?",
    description:
      "Alege magazinul și folosește Ce aleg? pentru scanare cod de bare, alternative și produse lipsă.",
    url: "/catalog-romania/magazine",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function CatalogStoresPage() {
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Magazine România în catalogul Ce aleg?",
    url: `${CATALOG_SEO_SITE_URL}/catalog-romania/magazine`,
    description:
      "Pagini publice pentru magazine unde utilizatorii pot scana produse și ajută la completarea catalogului.",
    mainEntity: SEO_STORES.map((store) => ({
      "@type": "Store",
      name: store.name,
      url: `${CATALOG_SEO_SITE_URL}/catalog-romania/magazine/${store.slug}`,
    })),
  };

  return (
    <>
      <JsonLd
        data={buildBreadcrumbJsonLd([
          { name: "Acasă", href: "/" },
          { name: "Catalog România", href: "/catalog-romania" },
          { name: "Magazine", href: "/catalog-romania/magazine" },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogStoresContent stores={SEO_STORES} />
    </>
  );
}

import {
  JsonLd,
  buildBreadcrumbJsonLd,
} from "../seo-components";
import { CATALOG_SEO_SITE_URL, SEO_ALTERNATIVE_GUIDES } from "../seo-data";
import { CatalogAlternativesContent } from "../CatalogHubContent";

export const metadata = {
  title: "Alternative la produse: ghiduri pentru cumpărături",
  description:
    "Ghiduri publice Ce aleg? pentru alternative la iaurturi dulci, dulciuri, băuturi cu zahăr, snacks, mezeluri și cereale.",
  alternates: {
    canonical: "/catalog-romania/alternative",
  },
  openGraph: {
    title: "Alternative la produse | Ce aleg?",
    description:
      "Ghiduri rapide pentru produse pe care le poți scana și compară la raft.",
    url: "/catalog-romania/alternative",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function AlternativesHubPage() {
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Alternative la produse",
    url: `${CATALOG_SEO_SITE_URL}/catalog-romania/alternative`,
    description:
      "Ghiduri publice despre alternative la produse alimentare, legate de scanarea codului de bare și catalogul Ce aleg?.",
    mainEntity: SEO_ALTERNATIVE_GUIDES.map((guide) => ({
      "@type": "Article",
      headline: guide.title,
      url: `${CATALOG_SEO_SITE_URL}/catalog-romania/alternative/${guide.slug}`,
    })),
  };

  return (
    <>
      <JsonLd
        data={buildBreadcrumbJsonLd([
          { name: "Acasă", href: "/" },
          { name: "Catalog România", href: "/catalog-romania" },
          { name: "Alternative", href: "/catalog-romania/alternative" },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogAlternativesContent guides={SEO_ALTERNATIVE_GUIDES} />
    </>
  );
}

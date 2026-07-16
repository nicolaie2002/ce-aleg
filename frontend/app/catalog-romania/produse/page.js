import {
  JsonLd,
  buildBreadcrumbJsonLd,
} from "../seo-components";
import { CATALOG_SEO_SITE_URL, SEO_PRODUCTS } from "../seo-data";
import { CatalogProductsContent } from "../CatalogHubContent";

export const metadata = {
  title: "Produse scanabile: exemple și pagini publice",
  description:
    "Pagini publice pentru produse scanabile în Ce aleg?: iaurturi, skyr, băuturi, batoane și produse care pot fi comparate după etichetă.",
  alternates: {
    canonical: "/catalog-romania/produse",
  },
  openGraph: {
    title: "Produse scanabile | Ce aleg?",
    description:
      "Exemple de produse pentru scanare cod de bare, verdict și alternative în catalogul Ce aleg?.",
    url: "/catalog-romania/produse",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function CatalogProductsPage() {
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Produse scanabile în Ce aleg?",
    url: `${CATALOG_SEO_SITE_URL}/catalog-romania/produse`,
    description:
      "Exemple publice de produse care pot fi căutate, scanate și comparate în Ce aleg?.",
    mainEntity: SEO_PRODUCTS.map((product) => ({
      "@type": "Product",
      name: product.name,
      image: `${CATALOG_SEO_SITE_URL}${product.image}`,
      url: `${CATALOG_SEO_SITE_URL}/catalog-romania/produse/${product.slug}`,
    })),
  };

  return (
    <>
      <JsonLd
        data={buildBreadcrumbJsonLd([
          { name: "Acasă", href: "/" },
          { name: "Catalog România", href: "/catalog-romania" },
          { name: "Produse", href: "/catalog-romania/produse" },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogProductsContent products={SEO_PRODUCTS} />
    </>
  );
}

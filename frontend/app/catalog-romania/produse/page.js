import { Barcode, Search } from "lucide-react";
import {
  CatalogSeoLayout,
  JsonLd,
  ProductCard,
  SeoCtaBand,
  SeoSection,
  buildBreadcrumbJsonLd,
} from "../seo-components";
import { CATALOG_SEO_SITE_URL, SEO_PRODUCTS } from "../seo-data";

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
      <CatalogSeoLayout
        eyebrow="Produse publice"
        title="Produse concrete pe care oamenii le pot caută și scana."
        description="Aceste pagini sunt exemple publice, bune pentru Google și pentru distribuit în grupuri. Nu promit stoc sau preț live; trimit utilizatorul spre scanare, comparare și contribuție când produsul lipsește."
        image="/products/iaurt-grecesc.jpg"
        imageAlt="Produse scanabile în catalogul Ce aleg?"
      >
        <SeoSection
          icon={Barcode}
          title="Exemple de produse"
        description="Fiecare pagină are scor orientativ, semnale de verificat, alternative și CTA către scanner."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {SEO_PRODUCTS.map((product) => (
              <ProductCard key={product.slug} product={product} />
            ))}
          </div>
        </SeoSection>

        <SeoSection
          icon={Search}
          title="De ce conteaza"
          description="Căutările organice sunt concrete: oamenii nu caută doar o aplicație, caută produse. Paginile acestea pot prinde termenii lungi și ii trimit spre folosirea aplicatiei."
        >
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "produs concret + verdict ușor de înțeles",
              "alternative apropiate pentru aceeași nevoie",
              "flow clar când produsul lipsește din catalog",
            ].map((item) => (
              <div key={item} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                <p className="text-sm font-bold leading-6 text-gray-200">{item}</p>
              </div>
            ))}
          </div>
        </SeoSection>

        <SeoCtaBand />
      </CatalogSeoLayout>
    </>
  );
}

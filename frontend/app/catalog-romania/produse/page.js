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
  title: "Produse scanabile: exemple si pagini publice",
  description:
    "Pagini publice pentru produse scanabile in Ce aleg?: iaurturi, skyr, bauturi, batoane si produse care pot fi comparate dupa eticheta.",
  alternates: {
    canonical: "/catalog-romania/produse",
  },
  openGraph: {
    title: "Produse scanabile | Ce aleg?",
    description:
      "Exemple de produse pentru scanare cod de bare, verdict si alternative in catalogul Ce aleg?.",
    url: "/catalog-romania/produse",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function CatalogProductsPage() {
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Produse scanabile in Ce aleg?",
    url: `${CATALOG_SEO_SITE_URL}/catalog-romania/produse`,
    description:
      "Exemple publice de produse care pot fi cautate, scanate si comparate in Ce aleg?.",
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
          { name: "Acasa", href: "/" },
          { name: "Catalog Romania", href: "/catalog-romania" },
          { name: "Produse", href: "/catalog-romania/produse" },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogSeoLayout
        eyebrow="Produse publice"
        title="Produse concrete pe care oamenii le pot cauta si scana."
        description="Aceste pagini sunt exemple publice, bune pentru Google si pentru distribuit in grupuri. Nu promit stoc sau pret live; trimit utilizatorul spre scanare, comparare si contributie cand produsul lipseste."
        image="/products/iaurt-grecesc.jpg"
        imageAlt="Produse scanabile in catalogul Ce aleg?"
      >
        <SeoSection
          icon={Barcode}
          title="Exemple de produse"
          description="Fiecare pagina are scor orientativ, semnale de verificat, alternative si CTA catre scanner."
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
          description="Cautarile organice sunt concrete: oamenii nu cauta doar o aplicatie, cauta produse. Paginile acestea pot prinde termenii lungi si ii trimit spre folosirea aplicatiei."
        >
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "produs concret + verdict usor de inteles",
              "alternative apropiate pentru aceeasi nevoie",
              "flow clar cand produsul lipseste din catalog",
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

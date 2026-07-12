import { Database, Search } from "lucide-react";
import {
  CatalogSeoLayout,
  CategoryCard,
  JsonLd,
  SeoCtaBand,
  SeoSection,
  buildBreadcrumbJsonLd,
} from "../seo-components";
import { CATALOG_SEO_SITE_URL, SEO_CATEGORIES } from "../seo-data";

export const metadata = {
  title: "Categorii produse Romania: scanare si alternative",
  description:
    "Ghid public pe categorii pentru produse din Romania: lactate, mezeluri, dulciuri, bauturi, conserve, panificatie si alte produse scanabile.",
  alternates: {
    canonical: "/catalog-romania/categorii",
  },
  openGraph: {
    title: "Categorii produse Romania | Ce aleg?",
    description:
      "Alege o categorie, scaneaza codul de bare si compara produse din aceeasi familie.",
    url: "/catalog-romania/categorii",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function CatalogCategoriesPage() {
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Categorii produse Romania",
    url: `${CATALOG_SEO_SITE_URL}/catalog-romania/categorii`,
    description:
      "Categorii publice pentru scanare produse, comparare etichete si completarea catalogului Ce aleg?.",
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
          { name: "Acasa", href: "/" },
          { name: "Catalog Romania", href: "/catalog-romania" },
          { name: "Categorii", href: "/catalog-romania/categorii" },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogSeoLayout
        eyebrow="Categorii publice"
        title="Categorii de produse pe care merita sa le scanezi."
        description="Fiecare categorie are probleme diferite: zahar la dulciuri, sare la mezeluri, proteina la lactate, ingrediente la produse bio. Paginile acestea sunt facute pentru cautari organice si pentru oameni care vor sa testeze aplicatia fara reclame."
        image="/products/skyr.webp"
        imageAlt="Produse scanabile in catalogul Ce aleg?"
      >
        <SeoSection
          icon={Database}
          title="Alege categoria"
          description="Paginile sunt statice, rapide si indexabile. Ele explica ce verifici la raft si trimit spre scanare sau contributii cand produsul lipseste."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SEO_CATEGORIES.map((category) => (
              <CategoryCard key={category.slug} category={category} />
            ))}
          </div>
        </SeoSection>

        <SeoSection
          icon={Search}
          title="Cum ajuta aceste pagini"
          description="Google poate indexa termeni mai specifici decat pagina principala: lactate Lidl, dulciuri fara mult zahar, conserve cu eticheta mai clara sau produse Penny scanabile."
        >
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "aduc trafic organic pe cautari concrete",
              "explica produsul inainte de inregistrare",
              "directioneaza utilizatorii spre scanare si catalog",
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

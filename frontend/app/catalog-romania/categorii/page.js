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
      <CatalogSeoLayout
        eyebrow="Categorii publice"
        title="Categorii de produse pe care merită să le scanezi."
        description="Fiecare categorie are probleme diferite: zahăr la dulciuri, sare la mezeluri, proteină la lactate, ingrediente la produse bio. Paginile acestea sunt facute pentru căutări organice și pentru oameni care vor să testeze aplicația fără reclame."
        image="/products/skyr.webp"
        imageAlt="Produse scanabile în catalogul Ce aleg?"
      >
        <SeoSection
          icon={Database}
          title="Alege categoria"
          description="Paginile sunt statice, rapide și indexabile. Ele explică ce verifici la raft și trimit spre scanare sau contribuții când produsul lipsește."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SEO_CATEGORIES.map((category) => (
              <CategoryCard key={category.slug} category={category} />
            ))}
          </div>
        </SeoSection>

        <SeoSection
          icon={Search}
          title="Cum ajută aceste pagini"
          description="Google poate indexa termeni mai specifici decât pagina principală: lactate Lidl, dulciuri fără mult zahăr, conserve cu etichetă mai clară sau produse Penny scanabile."
        >
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "aduc trafic organic pe căutări concrete",
              "explică produsul înainte de inregistrare",
              "directioneaza utilizatorii spre scanare și catalog",
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

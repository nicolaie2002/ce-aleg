import { Search, Store } from "lucide-react";
import {
  CatalogSeoLayout,
  JsonLd,
  SeoCtaBand,
  SeoSection,
  StoreCard,
  buildBreadcrumbJsonLd,
} from "../seo-components";
import { CATALOG_SEO_SITE_URL, SEO_STORES } from "../seo-data";

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
      <CatalogSeoLayout
        eyebrow="Magazine publice"
        title="Magazine din România unde poți folosi Ce aleg?."
        description="Fiecare pagină explică de ce merită să scanezi produse în acel magazin și ce categorii sunt potrivite pentru contribuții gratuite."
        image="/stores/any-store.png"
        imageAlt="Magazine România în catalogul Ce aleg?"
      >
        <SeoSection
          icon={Store}
          title="Alege magazinul"
          description="Paginile sunt publice și indexabile. Nu promit acoperire completă; arată cum folosești aplicația și unde comunitatea poate completa catalogul."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SEO_STORES.map((store) => (
              <StoreCard key={store.slug} store={store} />
            ))}
          </div>
        </SeoSection>

        <SeoSection
          icon={Search}
          title="De ce sunt utile pentru trafic gratuit"
          description="Oamenii caută produse prin numele magazinului. Aceste pagini pot prinde căutări organice fără buget de reclame."
        >
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "le poți distribui în grupuri fără să para reclama agresiva",
              "Google vede pagini clare pentru fiecare magazin",
              "CTA-ul trimite spre scanare sau produs negăsit",
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

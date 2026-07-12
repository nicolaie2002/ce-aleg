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
  title: "Magazine Romania: Lidl, Kaufland, Carrefour, Mega, Profi, Penny",
  description:
    "Pagini publice pentru magazine din Romania unde poti scana produse, compara alternative si contribui la catalogul Ce aleg?.",
  alternates: {
    canonical: "/catalog-romania/magazine",
  },
  openGraph: {
    title: "Magazine Romania | Catalog Ce aleg?",
    description:
      "Alege magazinul si foloseste Ce aleg? pentru scanare cod de bare, alternative si produse lipsa.",
    url: "/catalog-romania/magazine",
    images: ["/opengraph-image.png?v=20260623"],
  },
};

export default function CatalogStoresPage() {
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: "Magazine Romania in catalogul Ce aleg?",
    url: `${CATALOG_SEO_SITE_URL}/catalog-romania/magazine`,
    description:
      "Pagini publice pentru magazine unde utilizatorii pot scana produse si ajuta la completarea catalogului.",
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
          { name: "Acasa", href: "/" },
          { name: "Catalog Romania", href: "/catalog-romania" },
          { name: "Magazine", href: "/catalog-romania/magazine" },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogSeoLayout
        eyebrow="Magazine publice"
        title="Magazine din Romania unde poti folosi Ce aleg?."
        description="Fiecare pagina explica de ce merita sa scanezi produse in acel magazin si ce categorii sunt potrivite pentru contributii gratuite."
        image="/stores/any-store.png"
        imageAlt="Magazine Romania in catalogul Ce aleg?"
      >
        <SeoSection
          icon={Store}
          title="Alege magazinul"
          description="Paginile sunt publice si indexabile. Nu promit acoperire completa; arata cum folosesti aplicatia si unde comunitatea poate completa catalogul."
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
          description="Oamenii cauta produse prin numele magazinului. Aceste pagini pot prinde cautari organice fara buget de reclame."
        >
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "le poti distribui in grupuri fara sa para reclama agresiva",
              "Google vede pagini clare pentru fiecare magazin",
              "CTA-ul trimite spre scanare sau produs negasit",
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

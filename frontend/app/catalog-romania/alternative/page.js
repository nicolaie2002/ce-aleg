import { Search, Sparkles } from "lucide-react";
import {
  AlternativeGuideCard,
  CatalogSeoLayout,
  JsonLd,
  SeoCtaBand,
  SeoSection,
  buildBreadcrumbJsonLd,
} from "../seo-components";
import { CATALOG_SEO_SITE_URL, SEO_ALTERNATIVE_GUIDES } from "../seo-data";

export const metadata = {
  title: "Alternative la produse: ghiduri pentru cumparaturi",
  description:
    "Ghiduri publice Ce aleg? pentru alternative la iaurturi dulci, dulciuri, bauturi cu zahar, snacks, mezeluri si cereale.",
  alternates: {
    canonical: "/catalog-romania/alternative",
  },
  openGraph: {
    title: "Alternative la produse | Ce aleg?",
    description:
      "Ghiduri rapide pentru produse pe care le poti scana si compara la raft.",
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
      "Ghiduri publice despre alternative la produse alimentare, legate de scanarea codului de bare si catalogul Ce aleg?.",
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
          { name: "Acasa", href: "/" },
          { name: "Catalog Romania", href: "/catalog-romania" },
          { name: "Alternative", href: "/catalog-romania/alternative" },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogSeoLayout
        eyebrow="Ghiduri gratuite"
        title="Alternative la produse pe care oamenii chiar le cauta."
        description="Aceste pagini sunt gandite pentru trafic organic si postari gratuite: explicam ce verifici, ce produse poti scana si cum alegi o alternativa mai potrivita."
        image="/products/baton-proteic.jpg"
        imageAlt="Alternative la produse in Ce aleg?"
      >
        <SeoSection
          icon={Sparkles}
          title="Alege un ghid"
          description="Fiecare ghid este legat de categorii, produse exemplu si CTA spre scanner."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SEO_ALTERNATIVE_GUIDES.map((guide) => (
              <AlternativeGuideCard key={guide.slug} guide={guide} />
            ))}
          </div>
        </SeoSection>

        <SeoSection
          icon={Search}
          title="Cum se folosesc fara reclame"
          description="Le poti trimite direct in grupuri sau in comentarii cand cineva intreaba despre un produs. Sunt utile fara buget."
        >
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "raspund la cautari concrete de tip alternative la...",
              "duc utilizatorul spre scanare si catalog",
              "pot fi extinse cu produse reale aprobate in timp",
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

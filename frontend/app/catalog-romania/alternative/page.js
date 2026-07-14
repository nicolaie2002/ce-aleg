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
      <CatalogSeoLayout
        eyebrow="Ghiduri gratuite"
        title="Alternative la produse pe care oamenii chiar le caută."
        description="Aceste pagini sunt gândite pentru trafic organic și postări gratuite: explicam ce verifici, ce produse poți scana și cum alegi o alternativă mai potrivită."
        image="/products/baton-proteic.jpg"
        imageAlt="Alternative la produse în Ce aleg?"
      >
        <SeoSection
          icon={Sparkles}
          title="Alege un ghid"
          description="Fiecare ghid este legat de categorii, produse exemplu și CTA spre scanner."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SEO_ALTERNATIVE_GUIDES.map((guide) => (
              <AlternativeGuideCard key={guide.slug} guide={guide} />
            ))}
          </div>
        </SeoSection>

        <SeoSection
          icon={Search}
          title="Cum se folosesc fără reclame"
          description="Le poți trimite direct în grupuri sau în comentarii când cineva întreabă despre un produs. Sunt utile fără buget."
        >
          <div className="grid gap-3 md:grid-cols-3">
            {[
              "raspund la căutări concrete de tip alternative la...",
              "duc utilizatorul spre scanare și catalog",
              "pot fi extinse cu produse reale aprobate în timp",
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

import { notFound } from "next/navigation";
import { Barcode, CheckCircle2, Search, Store } from "lucide-react";
import {
  CatalogSeoLayout,
  CategoryStoreLinks,
  JsonLd,
  PillGrid,
  SeoCtaBand,
  SeoSection,
  StepList,
  buildBreadcrumbJsonLd,
} from "../../seo-components";
import {
  CATALOG_SEO_SITE_URL,
  SEO_CATEGORIES,
  getSeoCategory,
  getStoresForCategory,
} from "../../seo-data";

export function generateStaticParams() {
  return SEO_CATEGORIES.map((category) => ({ slug: category.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const category = getSeoCategory(slug);

  if (!category) {
    return {};
  }

  return {
    title: `${category.name}: scanare produse și alternative`,
    description: `${category.intro} Scanează codul de bare, compară eticheta și adaugă produse lipsă în catalogul Ce aleg?.`,
    alternates: {
      canonical: `/catalog-romania/categorii/${category.slug}`,
    },
    openGraph: {
      title: `${category.name} | Catalog România Ce aleg?`,
      description: category.intro,
      url: `/catalog-romania/categorii/${category.slug}`,
      images: [category.image],
    },
  };
}

export default async function CatalogCategoryPage({ params }) {
  const { slug } = await params;
  const category = getSeoCategory(slug);

  if (!category) {
    notFound();
  }

  const stores = getStoresForCategory(category);
  const pageUrl = `${CATALOG_SEO_SITE_URL}/catalog-romania/categorii/${category.slug}`;
  const collectionJsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `${category.name} în catalogul Ce aleg?`,
    url: pageUrl,
    description: category.intro,
    about: category.examples.map((example) => ({ "@type": "Thing", name: example })),
    potentialAction: {
      "@type": "SearchAction",
      target: `${CATALOG_SEO_SITE_URL}/scan?query={search_term_string}`,
      "query-input": "required name=search_term_string",
    },
  };

  return (
    <>
      <JsonLd
        data={buildBreadcrumbJsonLd([
          { name: "Acasă", href: "/" },
          { name: "Catalog România", href: "/catalog-romania" },
          { name: "Categorii", href: "/catalog-romania/categorii" },
          { name: category.name, href: `/catalog-romania/categorii/${category.slug}` },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogSeoLayout
        eyebrow="Ghid categorie"
        title={`${category.name}: scanează produse și compară alternative.`}
        description={category.intro}
        image={category.image}
        imageAlt={`${category.name} în catalogul Ce aleg?`}
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
          <SeoSection
            icon={Barcode}
            title="Ce merită verificat"
            description="Când două produse par aproape identice, diferența apare în nutrienți și ingrediente."
          >
            <PillGrid items={category.compareSignals} />
          </SeoSection>

          <SeoSection
            icon={Search}
            title="Exemple de căutări"
            description="Aceste produse sunt bune pentru scanare, căutare manuală sau completarea catalogului."
          >
            <PillGrid items={category.examples} tone="emerald" />
          </SeoSection>
        </div>

        <SeoSection
          icon={CheckCircle2}
          title="Flow recomandat la raft"
          description={category.advice}
        >
          <StepList
            items={[
              "Scanează codul de bare sau caută produsul după nume.",
              "Citește verdictul și compară scorul cu produse similare.",
              "Dacă produsul lipsește, trimite poze pentru verificare și primești CeCoins după aprobare.",
            ]}
          />
        </SeoSection>

        <SeoSection
          icon={Store}
          title={`Magazine unde categoria ${category.name.toLowerCase()} merită urmărită`}
          description="Legăturile interne ajută utilizatorii să ajungă rapid la magazinul în care fac cumpărături."
        >
          <CategoryStoreLinks stores={stores} />
        </SeoSection>

        <SeoCtaBand />
      </CatalogSeoLayout>
    </>
  );
}

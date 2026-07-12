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
    title: `${category.name}: scanare produse si alternative`,
    description: `${category.intro} Scaneaza codul de bare, compara eticheta si adauga produse lipsa in catalogul Ce aleg?.`,
    alternates: {
      canonical: `/catalog-romania/categorii/${category.slug}`,
    },
    openGraph: {
      title: `${category.name} | Catalog Romania Ce aleg?`,
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
    name: `${category.name} in catalogul Ce aleg?`,
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
          { name: "Acasa", href: "/" },
          { name: "Catalog Romania", href: "/catalog-romania" },
          { name: "Categorii", href: "/catalog-romania/categorii" },
          { name: category.name, href: `/catalog-romania/categorii/${category.slug}` },
        ])}
      />
      <JsonLd data={collectionJsonLd} />
      <CatalogSeoLayout
        eyebrow="Ghid categorie"
        title={`${category.name}: scaneaza produse si compara alternative.`}
        description={category.intro}
        image={category.image}
        imageAlt={`${category.name} in catalogul Ce aleg?`}
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
          <SeoSection
            icon={Barcode}
            title="Ce merita verificat"
            description="Cand doua produse par aproape identice, diferenta apare in nutrienti si ingrediente."
          >
            <PillGrid items={category.compareSignals} />
          </SeoSection>

          <SeoSection
            icon={Search}
            title="Exemple de cautari"
            description="Aceste produse sunt bune pentru scanare, cautare manuala sau completarea catalogului."
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
              "Scaneaza codul de bare sau cauta produsul dupa nume.",
              "Citeste verdictul si compara scorul cu produse similare.",
              "Daca produsul lipseste, trimite poze pentru verificare si primesti CeCoins dupa aprobare.",
            ]}
          />
        </SeoSection>

        <SeoSection
          icon={Store}
          title={`Magazine unde categoria ${category.name.toLowerCase()} merita urmarita`}
          description="Legaturile interne ajuta utilizatorii sa ajunga rapid la magazinul in care fac cumparaturi."
        >
          <CategoryStoreLinks stores={stores} />
        </SeoSection>

        <SeoCtaBand />
      </CatalogSeoLayout>
    </>
  );
}

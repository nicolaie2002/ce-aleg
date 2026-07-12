import { notFound } from "next/navigation";
import { Barcode, Database, Search, Store } from "lucide-react";
import {
  CatalogSeoLayout,
  JsonLd,
  PillGrid,
  SeoCtaBand,
  SeoSection,
  StepList,
  StoreCategoryLinks,
  buildBreadcrumbJsonLd,
} from "../../seo-components";
import {
  CATALOG_SEO_SITE_URL,
  SEO_STORES,
  getCategoriesForStore,
  getSeoStore,
} from "../../seo-data";

export function generateStaticParams() {
  return SEO_STORES.map((store) => ({ slug: store.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const store = getSeoStore(slug);

  if (!store) {
    return {};
  }

  return {
    title: `${store.name}: scanare produse si catalog Romania`,
    description: `${store.intro} Scaneaza coduri de bare, compara alternative si contribuie cu produse lipsa.`,
    alternates: {
      canonical: `/catalog-romania/magazine/${store.slug}`,
    },
    openGraph: {
      title: `${store.name} | Catalog Romania Ce aleg?`,
      description: store.intro,
      url: `/catalog-romania/magazine/${store.slug}`,
      images: [store.logo],
    },
  };
}

export default async function CatalogStorePage({ params }) {
  const { slug } = await params;
  const store = getSeoStore(slug);

  if (!store) {
    notFound();
  }

  const categories = getCategoriesForStore(store);
  const pageUrl = `${CATALOG_SEO_SITE_URL}/catalog-romania/magazine/${store.slug}`;
  const storeJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: `${store.name} in catalogul Ce aleg?`,
    url: pageUrl,
    description: store.intro,
    about: {
      "@type": "Store",
      name: store.name,
    },
    mainEntity: categories.map((category) => ({
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
          { name: "Magazine", href: "/catalog-romania/magazine" },
          { name: store.name, href: `/catalog-romania/magazine/${store.slug}` },
        ])}
      />
      <JsonLd data={storeJsonLd} />
      <CatalogSeoLayout
        eyebrow="Ghid magazin"
        title={`${store.name}: scaneaza produse si compara alternative.`}
        description={store.intro}
        image={store.logo}
        imageAlt={`${store.name} in catalogul Ce aleg?`}
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <SeoSection
            icon={Store}
            title="Pentru ce e util"
            description="Pagina nu inlocuieste catalogul live, ci explica modul de folosire si trimite catre scanare."
          >
            <PillGrid items={[store.shopperIntent]} />
          </SeoSection>

          <SeoSection
            icon={Search}
            title="Ce verifici la raft"
            description="Cand produsul lipseste, flow-ul de contributie ajuta catalogul sa creasca organic."
          >
            <PillGrid items={store.checks} tone="emerald" />
          </SeoSection>
        </div>

        <SeoSection
          icon={Barcode}
          title={`Cum folosesti Ce aleg? in ${store.name}`}
          description="Un flow simplu pentru telefon: alegi magazinul, scanezi, compari si contribui cand produsul lipseste."
        >
          <StepList
            items={[
              `Alege ${store.name} in modul La magazin sau intra direct in scanner.`,
              "Scaneaza codul de bare si verifica verdictul produsului.",
              "Daca produsul nu exista, confirma codul si trimite pozele pentru verificare.",
            ]}
          />
        </SeoSection>

        <SeoSection
          icon={Database}
          title={`Categorii utile in ${store.name}`}
          description="Aceste legaturi interne ajuta paginile sa fie mai clare pentru Google si mai rapide pentru utilizatori."
        >
          <StoreCategoryLinks categories={categories} />
        </SeoSection>

        <SeoCtaBand />
      </CatalogSeoLayout>
    </>
  );
}

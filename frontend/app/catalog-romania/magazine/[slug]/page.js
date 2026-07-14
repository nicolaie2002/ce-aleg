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
    title: `${store.name}: scanare produse și catalog România`,
    description: `${store.intro} Scanează coduri de bare, compară alternative și contribuie cu produse lipsă.`,
    alternates: {
      canonical: `/catalog-romania/magazine/${store.slug}`,
    },
    openGraph: {
      title: `${store.name} | Catalog România Ce aleg?`,
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
    name: `${store.name} în catalogul Ce aleg?`,
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
          { name: "Acasă", href: "/" },
          { name: "Catalog România", href: "/catalog-romania" },
          { name: "Magazine", href: "/catalog-romania/magazine" },
          { name: store.name, href: `/catalog-romania/magazine/${store.slug}` },
        ])}
      />
      <JsonLd data={storeJsonLd} />
      <CatalogSeoLayout
        eyebrow="Ghid magazin"
        title={`${store.name}: scanează produse și compară alternative.`}
        description={store.intro}
        image={store.logo}
        imageAlt={`${store.name} în catalogul Ce aleg?`}
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <SeoSection
            icon={Store}
            title="Pentru ce e util"
            description="Pagina nu înlocuiește catalogul live, ci explică modul de folosire și trimite către scanare."
          >
            <PillGrid items={[store.shopperIntent]} />
          </SeoSection>

          <SeoSection
            icon={Search}
            title="Ce verifici la raft"
            description="Când produsul lipsește, flow-ul de contribuție ajută catalogul să crească organic."
          >
            <PillGrid items={store.checks} tone="emerald" />
          </SeoSection>
        </div>

        <SeoSection
          icon={Barcode}
          title={`Cum folosești Ce aleg? în ${store.name}`}
          description="Un flow simplu pentru telefon: alegi magazinul, scanezi, compari și contribui când produsul lipsește."
        >
          <StepList
            items={[
              `Alege ${store.name} în modul La magazin sau intră direct în scanner.`,
              "Scanează codul de bare și verifică verdictul produsului.",
              "Dacă produsul nu există, confirmă codul și trimite pozele pentru verificare.",
            ]}
          />
        </SeoSection>

        <SeoSection
          icon={Database}
          title={`Categorii utile în ${store.name}`}
          description="Aceste legături interne ajută paginile să fie mai clare pentru Google și mai rapide pentru utilizatori."
        >
          <StoreCategoryLinks categories={categories} />
        </SeoSection>

        <SeoCtaBand />
      </CatalogSeoLayout>
    </>
  );
}

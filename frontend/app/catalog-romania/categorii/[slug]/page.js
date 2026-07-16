import { notFound } from "next/navigation";
import {
  JsonLd,
  buildBreadcrumbJsonLd,
} from "../../seo-components";
import {
  CATALOG_SEO_SITE_URL,
  SEO_CATEGORIES,
  getSeoCategory,
  getStoresForCategory,
} from "../../seo-data";
import { CatalogCategoryContent } from "../../CatalogDetailContent";

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { slug } = params;
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
  const { slug } = params;
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
      <CatalogCategoryContent category={category} stores={stores} />
    </>
  );
}

import { notFound } from "next/navigation";
import {
  JsonLd,
  buildBreadcrumbJsonLd,
} from "../../seo-components";
import {
  CATALOG_SEO_SITE_URL,
  SEO_STORES,
  getCategoriesForStore,
  getSeoStore,
} from "../../seo-data";
import { CatalogStoreContent } from "../StoreCatalogContent";

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
      <CatalogStoreContent store={store} categories={categories} />
    </>
  );
}

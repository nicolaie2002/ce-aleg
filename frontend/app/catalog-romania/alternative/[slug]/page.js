import { notFound } from "next/navigation";
import {
  JsonLd,
  buildBreadcrumbJsonLd,
} from "../../seo-components";
import {
  CATALOG_SEO_SITE_URL,
  SEO_ALTERNATIVE_GUIDES,
  getCategoriesForAlternativeGuide,
  getProductsForAlternativeGuide,
  getSeoAlternativeGuide,
} from "../../seo-data";
import { CatalogAlternativeContent } from "../../CatalogDetailContent";

export function generateStaticParams() {
  return SEO_ALTERNATIVE_GUIDES.map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const guide = getSeoAlternativeGuide(slug);

  if (!guide) {
    return {};
  }

  return {
    title: `${guide.title}: ce verifici și ce scanezi`,
    description: `${guide.intro} Ghid Ce aleg? pentru alternative, etichete și produse scanabile.`,
    alternates: {
      canonical: `/catalog-romania/alternative/${guide.slug}`,
    },
    openGraph: {
      title: `${guide.title} | Ce aleg?`,
      description: guide.intro,
      url: `/catalog-romania/alternative/${guide.slug}`,
      images: [guide.image],
    },
  };
}

export default async function AlternativeGuidePage({ params }) {
  const { slug } = await params;
  const guide = getSeoAlternativeGuide(slug);

  if (!guide) {
    notFound();
  }

  const products = getProductsForAlternativeGuide(guide);
  const categories = getCategoriesForAlternativeGuide(guide);
  const pageUrl = `${CATALOG_SEO_SITE_URL}/catalog-romania/alternative/${guide.slug}`;
  const articleJsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: guide.title,
    description: guide.intro,
    image: `${CATALOG_SEO_SITE_URL}${guide.image}`,
    url: pageUrl,
    author: {
      "@type": "Organization",
      name: "Ce aleg?",
      url: CATALOG_SEO_SITE_URL,
    },
    publisher: {
      "@type": "Organization",
      name: "Ce aleg?",
      logo: {
        "@type": "ImageObject",
        url: `${CATALOG_SEO_SITE_URL}/icon.png`,
      },
    },
  };

  return (
    <>
      <JsonLd
        data={buildBreadcrumbJsonLd([
          { name: "Acasă", href: "/" },
          { name: "Catalog România", href: "/catalog-romania" },
          { name: "Alternative", href: "/catalog-romania/alternative" },
          { name: guide.title, href: `/catalog-romania/alternative/${guide.slug}` },
        ])}
      />
      <JsonLd data={articleJsonLd} />
      <CatalogAlternativeContent
        guide={guide}
        products={products}
        categories={categories}
      />
    </>
  );
}

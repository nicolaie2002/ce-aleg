import { notFound } from "next/navigation";
import {
  JsonLd,
  buildBreadcrumbJsonLd,
} from "../../seo-components";
import {
  CATALOG_SEO_SITE_URL,
  SEO_PRODUCTS,
  getAlternativesForProduct,
  getSeoCategory,
  getSeoProduct,
  getSeoStore,
} from "../../seo-data";
import { CatalogProductContent } from "../../CatalogDetailContent";

export function generateStaticParams() {
  return SEO_PRODUCTS.map((product) => ({ slug: product.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const product = getSeoProduct(slug);

  if (!product) {
    return {};
  }

  return {
    title: `${product.name}: scor, eticheta și alternative`,
    description: `${product.intro} Vezi ce merită verificat, alternative și cum îl scanezi în Ce aleg?.`,
    alternates: {
      canonical: `/catalog-romania/produse/${product.slug}`,
    },
    openGraph: {
      title: `${product.name} | Ce aleg?`,
      description: product.verdict,
      url: `/catalog-romania/produse/${product.slug}`,
      images: [product.image],
    },
  };
}

export default async function CatalogProductPage({ params }) {
  const { slug } = await params;
  const product = getSeoProduct(slug);

  if (!product) {
    notFound();
  }

  const category = getSeoCategory(product.categorySlug);
  const stores = product.storeSlugs.map(getSeoStore).filter(Boolean);
  const alternatives = getAlternativesForProduct(product);
  const pageUrl = `${CATALOG_SEO_SITE_URL}/catalog-romania/produse/${product.slug}`;
  const productJsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    brand: product.brand,
    category: category?.name || "Produs alimentar",
    image: `${CATALOG_SEO_SITE_URL}${product.image}`,
    description: product.intro,
    url: pageUrl,
    additionalProperty: [
      {
        "@type": "PropertyValue",
        name: "Scor orientativ Ce aleg?",
        value: `${product.score}/10`,
      },
    ],
  };

  return (
    <>
      <JsonLd
        data={buildBreadcrumbJsonLd([
          { name: "Acasă", href: "/" },
          { name: "Catalog România", href: "/catalog-romania" },
          { name: "Produse", href: "/catalog-romania/produse" },
          { name: product.name, href: `/catalog-romania/produse/${product.slug}` },
        ])}
      />
      <JsonLd data={productJsonLd} />
      <CatalogProductContent
        product={product}
        category={category}
        stores={stores}
        alternatives={alternatives}
      />
    </>
  );
}

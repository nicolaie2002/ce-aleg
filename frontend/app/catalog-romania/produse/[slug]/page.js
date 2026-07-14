import { notFound } from "next/navigation";
import { Barcode, CheckCircle2, Database, Search, Store } from "lucide-react";
import {
  CatalogSeoLayout,
  CategoryStoreLinks,
  JsonLd,
  PillGrid,
  ProductCard,
  SeoCtaBand,
  SeoSection,
  StepList,
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
      <CatalogSeoLayout
        eyebrow="Pagina produs"
        title={`${product.name}: ce verifici înainte să îl cumperi.`}
        description={product.intro}
        image={product.image}
        imageAlt={product.name}
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
          <SeoSection
            icon={CheckCircle2}
            title={`Scor orientativ: ${product.score}/10`}
            description={product.verdict}
          >
            <PillGrid items={product.goodFor} tone="emerald" />
          </SeoSection>

          <SeoSection
            icon={Search}
            title="Ce merită urmărit pe etichetă"
            description="Paginile publice nu înlocuiesc eticheta reală. Scanează produsul când ești la raft pentru datele cele mai utile."
          >
            <PillGrid items={product.nutrients} />
          </SeoSection>
        </div>

        <SeoSection
          icon={Barcode}
          title="Flow recomandat"
          description="Dacă produsul există în catalog, primești verdict și alternative. Dacă lipsește, flow-ul de produs negăsit ajută comunitatea."
        >
          <StepList
            items={[
              "Scanează codul de bare sau caută produsul după nume.",
              "Compară scorul cu produse similare din aceeași categorie.",
              "Când produsul lipsește, confirmă codul și trimite pozele pentru verificare.",
            ]}
          />
        </SeoSection>

        <SeoSection
          icon={Database}
          title="Alternative apropiate"
          description="Aceste exemple ajută utilizatorul să înțeleagă ce poate compara în aplicație."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {alternatives.map((alternative) => (
              <ProductCard key={alternative.slug} product={alternative} />
            ))}
          </div>
        </SeoSection>

        {category ? (
          <SeoSection
            icon={Store}
            title={`Magazine și categorie pentru ${product.name}`}
            description={`Produsul este legat de categoria ${category.name}. Linkurile ajută navigarea și indexarea organică.`}
          >
            <CategoryStoreLinks stores={stores} />
          </SeoSection>
        ) : null}

        <SeoSection
          icon={Search}
          title="Semnale de atentie"
          description="Nu toate variantele aceluiași produs sunt identice. Verifică ambalajul real."
        >
          <PillGrid items={product.watchOut} />
        </SeoSection>

        <SeoCtaBand />
      </CatalogSeoLayout>
    </>
  );
}

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
    title: `${product.name}: scor, eticheta si alternative`,
    description: `${product.intro} Vezi ce merita verificat, alternative si cum il scanezi in Ce aleg?.`,
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
          { name: "Acasa", href: "/" },
          { name: "Catalog Romania", href: "/catalog-romania" },
          { name: "Produse", href: "/catalog-romania/produse" },
          { name: product.name, href: `/catalog-romania/produse/${product.slug}` },
        ])}
      />
      <JsonLd data={productJsonLd} />
      <CatalogSeoLayout
        eyebrow="Pagina produs"
        title={`${product.name}: ce verifici inainte sa il cumperi.`}
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
            title="Ce merita urmarit pe eticheta"
            description="Paginile publice nu inlocuiesc eticheta reala. Scaneaza produsul cand esti la raft pentru datele cele mai utile."
          >
            <PillGrid items={product.nutrients} />
          </SeoSection>
        </div>

        <SeoSection
          icon={Barcode}
          title="Flow recomandat"
          description="Daca produsul exista in catalog, primesti verdict si alternative. Daca lipseste, flow-ul de produs negasit ajuta comunitatea."
        >
          <StepList
            items={[
              "Scaneaza codul de bare sau cauta produsul dupa nume.",
              "Compara scorul cu produse similare din aceeasi categorie.",
              "Cand produsul lipseste, confirma codul si trimite pozele pentru verificare.",
            ]}
          />
        </SeoSection>

        <SeoSection
          icon={Database}
          title="Alternative apropiate"
          description="Aceste exemple ajuta utilizatorul sa inteleaga ce poate compara in aplicatie."
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
            title={`Magazine si categorie pentru ${product.name}`}
            description={`Produsul este legat de categoria ${category.name}. Linkurile ajuta navigarea si indexarea organica.`}
          >
            <CategoryStoreLinks stores={stores} />
          </SeoSection>
        ) : null}

        <SeoSection
          icon={Search}
          title="Semnale de atentie"
          description="Nu toate variantele aceluiasi produs sunt identice. Verifica ambalajul real."
        >
          <PillGrid items={product.watchOut} />
        </SeoSection>

        <SeoCtaBand />
      </CatalogSeoLayout>
    </>
  );
}

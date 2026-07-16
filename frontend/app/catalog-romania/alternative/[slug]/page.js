import { notFound } from "next/navigation";
import { Barcode, Database, Search, Sparkles } from "lucide-react";
import {
  CatalogSeoLayout,
  JsonLd,
  PillGrid,
  ProductCard,
  SeoCtaBand,
  SeoSection,
  StepList,
  StoreCategoryLinks,
  buildBreadcrumbJsonLd,
} from "../../seo-components";
import {
  CATALOG_SEO_SITE_URL,
  SEO_ALTERNATIVE_GUIDES,
  getCategoriesForAlternativeGuide,
  getProductsForAlternativeGuide,
  getSeoAlternativeGuide,
} from "../../seo-data";

export function generateStaticParams() {
  return SEO_ALTERNATIVE_GUIDES.map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = params;
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
  const { slug } = params;
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
      <CatalogSeoLayout
        eyebrow="Alternative la produse"
        title={`${guide.title}.`}
        description={guide.intro}
        image={guide.image}
        imageAlt={guide.title}
      >
        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <SeoSection
            icon={Search}
            title="Pentru ce cautare e util"
            description={guide.searchIntent}
          >
            <PillGrid items={guide.checks} />
          </SeoSection>

          <SeoSection
            icon={Sparkles}
            title="Cum alegi alternativă"
            description="Nu cautam produsul perfect, ci varianta mai potrivită pentru contextul tău."
          >
            <StepList
              items={[
                "Scanează produsul pe care voiai să îl cumperi.",
                "Verifică zahărul, sarea, proteina, ingredientele sau semnalul relevant.",
                "Compară alternative apropiate și salvează produsul care se potrivește.",
              ]}
            />
          </SeoSection>
        </div>

        <SeoSection
          icon={Barcode}
          title="Produse exemplu pentru comparatie"
          description="Aceste carduri arata tipul de decizie pe care aplicația o poate ajută la raft."
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {products.map((product) => (
              <ProductCard key={product.slug} product={product} />
            ))}
          </div>
        </SeoSection>

        <SeoSection
          icon={Database}
          title="Categorii legate"
          description="Ghidul este legat de paginile de categorie pentru navigare și indexare."
        >
          <StoreCategoryLinks categories={categories} />
        </SeoSection>

        <SeoCtaBand />
      </CatalogSeoLayout>
    </>
  );
}

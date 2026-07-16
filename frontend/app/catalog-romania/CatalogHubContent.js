"use client";

import { useMemo } from "react";
import { Barcode, Database, Search, Sparkles } from "lucide-react";
import { useLocale } from "../components/LocaleProvider";
import {
  AlternativeGuideCard,
  CatalogSeoLayout,
  CategoryCard,
  ProductCard,
  SeoCtaBand,
  SeoSection,
} from "./seo-components";
import {
  getLocalizedSeoAlternativeGuide,
  getLocalizedSeoCategory,
  getLocalizedSeoProduct,
} from "./seo-data";

function LocalizedLayout({ children, ...props }) {
  const { pick } = useLocale();

  return (
    <CatalogSeoLayout
      {...props}
      actionLabel={pick("Scanează", "Scan")}
      catalogLabel={pick("Catalog România", "Romania catalog")}
      primaryActionLabel={pick("Scanează un produs", "Scan a product")}
      secondaryActionLabel={pick("Adaugă produs lipsă", "Add missing product")}
      mediaCaption={pick(
        "Scanare cod de bare, alternative și catalog construit de comunitate.",
        "Barcode scanning, alternatives and a community-built catalog."
      )}
    >
      {children}
    </CatalogSeoLayout>
  );
}

function LocalizedCta() {
  const { pick } = useLocale();

  return (
    <SeoCtaBand
      eyebrow={pick("Catalogul crește gratuit", "The catalog grows for free")}
      title={pick(
        "Produs negăsit? Trimite-l la verificare și ajută catalogul pentru România.",
        "Product not found? Submit it for review and help build Romania's catalog."
      )}
      description={pick(
        "Produsele reale scanate de utilizatori fac aplicația mai utilă pentru toți.",
        "Real products scanned by users make the app more useful for everyone."
      )}
      buttonLabel={pick("Trimite produs", "Submit product")}
    />
  );
}

function ReasonGrid({ items }) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {items.map((item) => (
        <div key={item} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
          <p className="text-sm font-bold leading-6 text-gray-200">{item}</p>
        </div>
      ))}
    </div>
  );
}

export function CatalogCategoriesContent({ categories }) {
  const { locale, pick } = useLocale();
  const localizedCategories = useMemo(
    () => categories.map((item) => getLocalizedSeoCategory(item, locale)),
    [categories, locale]
  );

  return (
    <LocalizedLayout
      eyebrow={pick("Categorii publice", "Public categories")}
      title={pick(
        "Categorii de produse pe care merită să le scanezi.",
        "Product categories worth scanning."
      )}
      description={pick(
        "Fiecare categorie are semnale diferite de verificat, de la zahăr și sare până la proteină și ingrediente.",
        "Each category has different signals to check, from sugar and salt to protein and ingredients."
      )}
      image="/products/skyr.webp"
      imageAlt={pick("Produse scanabile în catalogul Ce aleg?", "Products available to scan in the Ce aleg? catalog")}
    >
      <SeoSection
        icon={Database}
        title={pick("Alege categoria", "Choose a category")}
        description={pick(
          "Află ce verifici la raft și pornește direct scanarea sau contribuția pentru un produs lipsă.",
          "See what to check on the shelf and start scanning or submit a missing product."
        )}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {localizedCategories.map((category) => (
            <CategoryCard
              key={category.slug}
              category={category}
              ctaLabel={pick("Vezi ghidul", "View guide")}
            />
          ))}
        </div>
      </SeoSection>

      <SeoSection
        icon={Search}
        title={pick("Cum te ajută aceste pagini", "How these pages help")}
        description={pick(
          "Găsești mai repede informația potrivită și ajungi direct la fluxul util.",
          "Find the right information faster and go straight to the useful flow."
        )}
      >
        <ReasonGrid
          items={[
            pick("răspund căutărilor concrete despre produse", "answer specific product searches"),
            pick("explică categoria înainte de înregistrare", "explain the category before sign-up"),
            pick("duc direct spre scanare și catalog", "lead directly to scanning and the catalog"),
          ]}
        />
      </SeoSection>

      <LocalizedCta />
    </LocalizedLayout>
  );
}

export function CatalogProductsContent({ products }) {
  const { locale, pick } = useLocale();
  const localizedProducts = useMemo(
    () => products.map((item) => getLocalizedSeoProduct(item, locale)),
    [locale, products]
  );

  return (
    <LocalizedLayout
      eyebrow={pick("Produse publice", "Public products")}
      title={pick(
        "Produse concrete pe care le poți căuta și scana.",
        "Real products you can search for and scan."
      )}
      description={pick(
        "Exemplele publice explică verdictul și alternativele, fără să promită stoc sau preț în timp real.",
        "Public examples explain the verdict and alternatives without promising real-time stock or prices."
      )}
      image="/products/iaurt-grecesc.jpg"
      imageAlt={pick("Produse scanabile în catalogul Ce aleg?", "Scannable products in the Ce aleg? catalog")}
    >
      <SeoSection
        icon={Barcode}
        title={pick("Exemple de produse", "Product examples")}
        description={pick(
          "Fiecare pagină are un scor orientativ, semnale de verificat și acces rapid la scanner.",
          "Each page includes an indicative score, signals to check and quick access to the scanner."
        )}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {localizedProducts.map((product) => (
            <ProductCard
              key={product.slug}
              product={product}
              ctaLabel={pick("Vezi pagina produsului", "View product page")}
            />
          ))}
        </div>
      </SeoSection>

      <SeoSection
        icon={Search}
        title={pick("De ce contează", "Why it matters")}
        description={pick(
          "Oamenii caută produse concrete. De aici pot ajunge direct la comparația din aplicație.",
          "People search for specific products. From here they can go straight to an in-app comparison."
        )}
      >
        <ReasonGrid
          items={[
            pick("produs concret și verdict ușor de înțeles", "specific product with an easy-to-understand verdict"),
            pick("alternative apropiate pentru aceeași nevoie", "similar alternatives for the same need"),
            pick("flux clar când produsul lipsește", "a clear flow when the product is missing"),
          ]}
        />
      </SeoSection>

      <LocalizedCta />
    </LocalizedLayout>
  );
}

export function CatalogAlternativesContent({ guides }) {
  const { locale, pick } = useLocale();
  const localizedGuides = useMemo(
    () => guides.map((item) => getLocalizedSeoAlternativeGuide(item, locale)),
    [guides, locale]
  );

  return (
    <LocalizedLayout
      eyebrow={pick("Ghiduri gratuite", "Free guides")}
      title={pick(
        "Alternative la produse pe care oamenii chiar le caută.",
        "Product alternatives people actually search for."
      )}
      description={pick(
        "Află ce verifici, ce produse poți scana și cum alegi o variantă mai potrivită.",
        "See what to check, which products you can scan and how to choose a better fit."
      )}
      image="/products/baton-proteic.jpg"
      imageAlt={pick("Alternative la produse în Ce aleg?", "Product alternatives in Ce aleg?")}
    >
      <SeoSection
        icon={Sparkles}
        title={pick("Alege un ghid", "Choose a guide")}
        description={pick(
          "Fiecare ghid este legat de categorii, produse exemplu și scanner.",
          "Each guide links to categories, example products and the scanner."
        )}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {localizedGuides.map((guide) => (
            <AlternativeGuideCard
              key={guide.slug}
              guide={guide}
              eyebrow={pick("Ghid alternative", "Alternatives guide")}
              ctaLabel={pick("Vezi ghidul", "View guide")}
            />
          ))}
        </div>
      </SeoSection>

      <SeoSection
        icon={Search}
        title={pick("Cum folosești ghidurile", "How to use the guides")}
        description={pick(
          "Pornește de la nevoia ta, apoi scanează produsul real pentru date actuale.",
          "Start with your need, then scan the real product for current data."
        )}
      >
        <ReasonGrid
          items={[
            pick("răspund căutărilor despre alternative", "answer searches about alternatives"),
            pick("duc direct spre scanare și catalog", "lead directly to scanning and the catalog"),
            pick("se extind cu produse reale aprobate", "grow with approved real products"),
          ]}
        />
      </SeoSection>

      <LocalizedCta />
    </LocalizedLayout>
  );
}

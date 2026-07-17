"use client";

import { useMemo } from "react";
import { Barcode, CheckCircle2, Database, Search, Sparkles, Store } from "lucide-react";
import { useLocale } from "../components/LocaleProvider";
import {
  CatalogSeoLayout,
  CategoryStoreLinks,
  PillGrid,
  ProductCard,
  SeoCtaBand,
  SeoSection,
  StepList,
  StoreCategoryLinks,
} from "./seo-components";
import {
  getLocalizedSeoAlternativeGuide,
  getLocalizedSeoCategory,
  getLocalizedSeoProduct,
  getLocalizedSeoStore,
} from "./seo-data";

/** @param {import("react").ComponentProps<typeof CatalogSeoLayout>} props */
function DetailLayout({ children, ...props }) {
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

function DetailCta() {
  const { pick } = useLocale();

  return (
    <SeoCtaBand
      eyebrow={pick("Catalogul crește gratuit", "The catalog grows for free")}
      title={pick(
        "Produs negăsit? Trimite-l la verificare și ajută catalogul pentru România.",
        "Product not found? Submit it for review and help build Romania's catalog."
      )}
      description={pick(
        "Produsele reale trimise de comunitate fac rezultatele mai utile pentru toți.",
        "Real products submitted by the community make results more useful for everyone."
      )}
      buttonLabel={pick("Trimite produs", "Submit product")}
    />
  );
}

export function CatalogCategoryContent({ category, stores }) {
  const { locale, pick } = useLocale();
  const localizedCategory = useMemo(
    () => getLocalizedSeoCategory(category, locale),
    [category, locale]
  );
  const localizedStores = useMemo(
    () => stores.map((item) => getLocalizedSeoStore(item, locale)),
    [locale, stores]
  );

  return (
    <DetailLayout
      eyebrow={pick("Ghid categorie", "Category guide")}
      title={pick(
        `${localizedCategory.name}: scanează produse și compară alternative.`,
        `${localizedCategory.name}: scan products and compare alternatives.`
      )}
      description={localizedCategory.intro}
      image={localizedCategory.image}
      imageAlt={pick(
        `${localizedCategory.name} în catalogul Ce aleg?`,
        `${localizedCategory.name} in the Ce aleg? catalog`
      )}
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <SeoSection
          icon={Barcode}
          title={pick("Ce merită verificat", "What to check")}
          description={pick(
            "Când două produse par identice, diferența apare în nutrienți și ingrediente.",
            "When two products look alike, the difference is often in nutrients and ingredients."
          )}
        >
          <PillGrid items={localizedCategory.compareSignals} />
        </SeoSection>
        <SeoSection
          icon={Search}
          title={pick("Exemple de căutări", "Search examples")}
          description={pick(
            "Folosește scanarea, căutarea manuală sau contribuția pentru un produs lipsă.",
            "Use scanning, manual search or submit a missing product."
          )}
        >
          <PillGrid items={localizedCategory.examples} tone="emerald" />
        </SeoSection>
      </div>

      <SeoSection
        icon={CheckCircle2}
        title={pick("Flux recomandat la raft", "Recommended shelf flow")}
        description={localizedCategory.advice}
      >
        <StepList
          items={[
            pick("Scanează codul de bare sau caută produsul după nume.", "Scan the barcode or search by product name."),
            pick("Citește verdictul și compară scorul cu produse similare.", "Read the verdict and compare the score with similar products."),
            pick("Dacă produsul lipsește, trimite poze și primești CeCoins după aprobare.", "If the product is missing, submit photos and earn CeCoins after approval."),
          ]}
        />
      </SeoSection>

      <SeoSection
        icon={Store}
        title={pick(
          `Magazine unde merită urmărită categoria ${localizedCategory.name.toLowerCase()}`,
          `Stores where ${localizedCategory.name.toLowerCase()} is worth checking`
        )}
        description={pick(
          "Alege magazinul în care faci cumpărături și continuă spre scanare.",
          "Choose the store where you shop and continue to scanning."
        )}
      >
        <CategoryStoreLinks stores={localizedStores} />
      </SeoSection>

      <DetailCta />
    </DetailLayout>
  );
}

export function CatalogProductContent({ product, category, stores, alternatives }) {
  const { locale, pick } = useLocale();
  const localizedProduct = useMemo(() => getLocalizedSeoProduct(product, locale), [locale, product]);
  const localizedCategory = useMemo(
    () => (category ? getLocalizedSeoCategory(category, locale) : null),
    [category, locale]
  );
  const localizedStores = useMemo(
    () => stores.map((item) => getLocalizedSeoStore(item, locale)),
    [locale, stores]
  );
  const localizedAlternatives = useMemo(
    () => alternatives.map((item) => getLocalizedSeoProduct(item, locale)),
    [alternatives, locale]
  );

  return (
    <DetailLayout
      eyebrow={pick("Pagina produsului", "Product page")}
      title={pick(
        `${localizedProduct.name}: ce verifici înainte să îl cumperi.`,
        `${localizedProduct.name}: what to check before buying.`
      )}
      description={localizedProduct.intro}
      image={localizedProduct.image}
      imageAlt={localizedProduct.name}
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <SeoSection
          icon={CheckCircle2}
          title={pick(`Scor orientativ: ${localizedProduct.score}/10`, `Indicative score: ${localizedProduct.score}/10`)}
          description={localizedProduct.verdict}
        >
          <PillGrid items={localizedProduct.goodFor} tone="emerald" />
        </SeoSection>
        <SeoSection
          icon={Search}
          title={pick("Ce merită urmărit pe etichetă", "What to check on the label")}
          description={pick(
            "Scanează ambalajul real la raft pentru cele mai utile date.",
            "Scan the real package on the shelf for the most useful data."
          )}
        >
          <PillGrid items={localizedProduct.nutrients} />
        </SeoSection>
      </div>

      <SeoSection
        icon={Barcode}
        title={pick("Flux recomandat", "Recommended flow")}
        description={pick(
          "Primești verdict și alternative când produsul există, iar când lipsește îl poți trimite la verificare.",
          "Get a verdict and alternatives when the product exists, or submit it for review when it is missing."
        )}
      >
        <StepList
          items={[
            pick("Scanează codul de bare sau caută produsul după nume.", "Scan the barcode or search by product name."),
            pick("Compară scorul cu produse similare din aceeași categorie.", "Compare the score with similar products in the same category."),
            pick("Dacă lipsește, confirmă codul și trimite pozele pentru verificare.", "If it is missing, confirm the barcode and submit photos for review."),
          ]}
        />
      </SeoSection>

      <SeoSection
        icon={Database}
        title={pick("Alternative apropiate", "Similar alternatives")}
        description={pick(
          "Compară produse apropiate înainte de a lua decizia la raft.",
          "Compare similar products before making your shelf decision."
        )}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {localizedAlternatives.map((item) => (
            <ProductCard
              key={item.slug}
              product={item}
              ctaLabel={pick("Vezi pagina produsului", "View product page")}
            />
          ))}
        </div>
      </SeoSection>

      {localizedCategory ? (
        <SeoSection
          icon={Store}
          title={pick(
            `Magazine și categorie pentru ${localizedProduct.name}`,
            `Stores and category for ${localizedProduct.name}`
          )}
          description={pick(
            `Produsul face parte din categoria ${localizedCategory.name}.`,
            `This product is part of the ${localizedCategory.name} category.`
          )}
        >
          <CategoryStoreLinks stores={localizedStores} />
        </SeoSection>
      ) : null}

      <SeoSection
        icon={Search}
        title={pick("Semnale de atenție", "Signals to watch")}
        description={pick(
          "Variantele aceluiași produs pot avea etichete diferite. Verifică ambalajul real.",
          "Variants of the same product may have different labels. Check the real package."
        )}
      >
        <PillGrid items={localizedProduct.watchOut} />
      </SeoSection>

      <DetailCta />
    </DetailLayout>
  );
}

export function CatalogAlternativeContent({ guide, products, categories }) {
  const { locale, pick } = useLocale();
  const localizedGuide = useMemo(
    () => getLocalizedSeoAlternativeGuide(guide, locale),
    [guide, locale]
  );
  const localizedProducts = useMemo(
    () => products.map((item) => getLocalizedSeoProduct(item, locale)),
    [locale, products]
  );
  const localizedCategories = useMemo(
    () => categories.map((item) => getLocalizedSeoCategory(item, locale)),
    [categories, locale]
  );

  return (
    <DetailLayout
      eyebrow={pick("Alternative la produse", "Product alternatives")}
      title={`${localizedGuide.title}.`}
      description={localizedGuide.intro}
      image={localizedGuide.image}
      imageAlt={localizedGuide.title}
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <SeoSection
          icon={Search}
          title={pick("Pentru ce căutare este util", "What this guide helps you find")}
          description={localizedGuide.searchIntent}
        >
          <PillGrid items={localizedGuide.checks} />
        </SeoSection>
        <SeoSection
          icon={Sparkles}
          title={pick("Cum alegi alternativa", "How to choose an alternative")}
          description={pick(
            "Caută varianta potrivită contextului tău, nu un produs perfect.",
            "Look for the option that fits your context, not a perfect product."
          )}
        >
          <StepList
            items={[
              pick("Scanează produsul pe care voiai să îl cumperi.", "Scan the product you intended to buy."),
              pick("Verifică semnalul relevant: zahăr, sare, proteină sau ingrediente.", "Check the relevant signal: sugar, salt, protein or ingredients."),
              pick("Compară alternative apropiate și salvează varianta potrivită.", "Compare similar alternatives and save the best fit."),
            ]}
          />
        </SeoSection>
      </div>

      <SeoSection
        icon={Barcode}
        title={pick("Produse exemplu pentru comparație", "Example products to compare")}
        description={pick(
          "Cardurile arată tipul de decizie pe care aplicația îl poate susține la raft.",
          "These cards show the kind of shelf decision the app can support."
        )}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {localizedProducts.map((item) => (
            <ProductCard
              key={item.slug}
              product={item}
              ctaLabel={pick("Vezi pagina produsului", "View product page")}
            />
          ))}
        </div>
      </SeoSection>

      <SeoSection
        icon={Database}
        title={pick("Categorii asociate", "Related categories")}
        description={pick(
          "Continuă către ghidurile de categorie pentru mai multe comparații.",
          "Continue to category guides for more comparisons."
        )}
      >
        <StoreCategoryLinks categories={localizedCategories} />
      </SeoSection>

      <DetailCta />
    </DetailLayout>
  );
}

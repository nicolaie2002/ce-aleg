"use client";

import { useMemo } from "react";
import { Barcode, Database, Search, Store } from "lucide-react";
import { useLocale } from "../../components/LocaleProvider";
import {
  CatalogSeoLayout,
  PillGrid,
  SeoCtaBand,
  SeoSection,
  StepList,
  StoreCard,
  StoreCategoryLinks,
} from "../seo-components";
import {
  getLocalizedSeoCategory,
  getLocalizedSeoStore,
} from "../seo-data";

/** @param {import("react").ComponentProps<typeof CatalogSeoLayout>} props */
function CatalogLayout({ children, ...props }) {
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

function LocalizedCatalogCta() {
  const { pick } = useLocale();

  return (
    <SeoCtaBand
      eyebrow={pick("Catalogul crește gratuit", "The catalog grows for free")}
      title={pick(
        "Produs negăsit? Trimite-l la verificare și ajută catalogul pentru România.",
        "Product not found? Submit it for review and help build Romania's catalog."
      )}
      description={pick(
        "Nu trebuie să așteptăm liste de la retaileri. Produsele reale scanate de utilizatori fac aplicația mai utilă pentru toți.",
        "We do not have to wait for retailer feeds. Real products scanned by users make the app more useful for everyone."
      )}
      buttonLabel={pick("Trimite produs", "Submit product")}
    />
  );
}

export function CatalogStoresContent({ stores }) {
  const { locale, pick } = useLocale();
  const localizedStores = useMemo(
    () => stores.map((store) => getLocalizedSeoStore(store, locale)),
    [locale, stores]
  );

  const trafficReasons = [
    pick(
      "le poți distribui în grupuri fără să pară reclamă agresivă",
      "you can share them in groups without making them feel like aggressive advertising"
    ),
    pick(
      "Google vede pagini clare pentru fiecare magazin",
      "Google sees a clear page for every store"
    ),
    pick(
      "acțiunile trimit direct spre scanare sau produs negăsit",
      "the actions lead directly to scanning or submitting a missing product"
    ),
  ];

  return (
    <CatalogLayout
      eyebrow={pick("Magazine publice", "Public stores")}
      title={pick(
        "Magazine din România unde poți folosi Ce aleg?.",
        "Stores in Romania where you can use Ce aleg?."
      )}
      description={pick(
        "Fiecare pagină explică de ce merită să scanezi produse în acel magazin și ce categorii sunt potrivite pentru contribuții gratuite.",
        "Each page explains why scanning products in that store is useful and which categories are best suited for free contributions."
      )}
      image="/stores/any-store.png"
      imageAlt={pick("Magazine România în catalogul Ce aleg?", "Romanian stores in the Ce aleg? catalog")}
    >
      <SeoSection
        icon={Store}
        title={pick("Alege magazinul", "Choose a store")}
        description={pick(
          "Paginile sunt publice și indexabile. Nu promit acoperire completă; arată cum folosești aplicația și unde comunitatea poate completa catalogul.",
          "These pages are public and indexable. They do not promise complete coverage; they show how to use the app and where the community can fill catalog gaps."
        )}
      >
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {localizedStores.map((store) => (
            <StoreCard
              key={store.slug}
              store={store}
              ctaLabel={pick("Vezi pagina magazinului", "View store page")}
            />
          ))}
        </div>
      </SeoSection>

      <SeoSection
        icon={Search}
        title={pick("De ce sunt utile pentru trafic gratuit", "Why these pages help organic traffic")}
        description={pick(
          "Oamenii caută produse prin numele magazinului. Aceste pagini pot răspunde căutărilor organice fără buget de reclame.",
          "People search for products by store name. These pages can answer organic searches without an advertising budget."
        )}
      >
        <div className="grid gap-3 md:grid-cols-3">
          {trafficReasons.map((item) => (
            <div key={item} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
              <p className="text-sm font-bold leading-6 text-gray-200">{item}</p>
            </div>
          ))}
        </div>
      </SeoSection>

      <LocalizedCatalogCta />
    </CatalogLayout>
  );
}

export function CatalogStoreContent({ store, categories }) {
  const { locale, pick } = useLocale();
  const localizedStore = useMemo(
    () => getLocalizedSeoStore(store, locale),
    [locale, store]
  );
  const localizedCategories = useMemo(
    () => categories.map((category) => getLocalizedSeoCategory(category, locale)),
    [categories, locale]
  );

  return (
    <CatalogLayout
      eyebrow={pick("Ghid magazin", "Store guide")}
      title={pick(
        `${localizedStore.name}: scanează produse și compară alternative.`,
        `${localizedStore.name}: scan products and compare alternatives.`
      )}
      description={localizedStore.intro}
      image={localizedStore.logo}
      imageAlt={pick(
        `${localizedStore.name} în catalogul Ce aleg?`,
        `${localizedStore.name} in the Ce aleg? catalog`
      )}
    >
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <SeoSection
          icon={Store}
          title={pick("Pentru ce e util", "What it is useful for")}
          description={pick(
            "Pagina explică modul de folosire și te trimite direct către scanarea catalogului live.",
            "This page explains how to use the app and takes you directly to the live catalog scanner."
          )}
        >
          <PillGrid items={[localizedStore.shopperIntent]} />
        </SeoSection>

        <SeoSection
          icon={Search}
          title={pick("Ce verifici la raft", "What to check on the shelf")}
          description={pick(
            "Când produsul lipsește, fluxul de contribuție ajută catalogul să crească organic.",
            "When a product is missing, the contribution flow helps the catalog grow organically."
          )}
        >
          <PillGrid items={localizedStore.checks} tone="emerald" />
        </SeoSection>
      </div>

      <SeoSection
        icon={Barcode}
        title={pick(
          `Cum folosești Ce aleg? în ${localizedStore.name}`,
          `How to use Ce aleg? in ${localizedStore.name}`
        )}
        description={pick(
          "Un flux simplu pentru telefon: alegi magazinul, scanezi, compari și contribui când produsul lipsește.",
          "A simple mobile flow: choose the store, scan, compare and contribute when a product is missing."
        )}
      >
        <StepList
          items={[
            pick(
              `Alege ${localizedStore.name} în modul La magazin sau intră direct în scanner.`,
              `Choose ${localizedStore.name} in Store mode or open the scanner directly.`
            ),
            pick(
              "Scanează codul de bare și verifică verdictul produsului.",
              "Scan the barcode and check the product verdict."
            ),
            pick(
              "Dacă produsul nu există, confirmă codul și trimite pozele pentru verificare.",
              "If the product is missing, confirm the barcode and submit the photos for review."
            ),
          ]}
        />
      </SeoSection>

      <SeoSection
        icon={Database}
        title={pick(
          `Categorii utile în ${localizedStore.name}`,
          `Useful categories in ${localizedStore.name}`
        )}
        description={pick(
          "Aceste legături te ajută să compari rapid categorii potrivite pentru cumpărăturile din acest magazin.",
          "These links help you quickly compare categories relevant to shopping in this store."
        )}
      >
        <StoreCategoryLinks categories={localizedCategories} />
      </SeoSection>

      <LocalizedCatalogCta />
    </CatalogLayout>
  );
}

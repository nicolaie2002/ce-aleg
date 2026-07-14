export const CATALOG_SEO_SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop"
).replace(/\/$/, "");

export const SEO_STORES = [
  {
    slug: "lidl",
    storeId: "lidl",
    name: "Lidl",
    logo: "/stores/lidl.png",
    tagline: "Produse de zi cu zi, multe mărci proprii și prețuri care merită comparate.",
    intro:
      "Pagina ajută utilizatorii care caută produse Lidl în România să înțeleagă cum pot scana codul de bare, compara eticheta și contribui cu produse lipsă în catalogul Ce aleg?.",
    shopperIntent: "bun pentru lactate, snacks, dulciuri, băuturi și produse de bază",
    checks: [
      "compară zahărul la iaurturi, cereale și gustări",
      "verifică proteina și ingredientele la produse proteice",
      "adaugă produse lipsă când scanezi un cod nou",
    ],
    categorySlugs: ["lactate", "dulciuri", "snacks", "bauturi", "cereale"],
  },
  {
    slug: "kaufland",
    storeId: "kaufland",
    name: "Kaufland",
    logo: "/stores/kaufland.png",
    tagline: "Coșuri mari, multe categorii și alternative apropiate la raft.",
    intro:
      "Pentru Kaufland, Ce aleg? poate fi folosit ca asistent rapid de scanare când ai multe produse similare și vrei să alegi varianta mai potrivită.",
    shopperIntent: "bun pentru lactate, conserve, panificație, băuturi și produse pentru familie",
    checks: [
      "scanează produse similare înainte să alegi baxul sau formatul mare",
      "urmărește scorul, zahărul, sarea și ingredientele importante",
      "trimite la verificare produsele care lipsesc din catalog",
    ],
    categorySlugs: ["lactate", "conserve", "panificatie", "bauturi", "mezeluri"],
  },
  {
    slug: "carrefour",
    storeId: "carrefour",
    name: "Carrefour",
    logo: "/stores/carrefour.png",
    tagline: "Multe branduri și produse similare, potrivite pentru comparații rapide.",
    intro:
      "În Carrefour poți folosi Ce aleg? ca să compari produse apropiate ca preț sau categorie și să găsești alternative mai clare pentru preferințele tale.",
    shopperIntent: "bun pentru dulciuri, snacks, băuturi, lactate și produse bio",
    checks: [
      "caută alternative când eticheta pare greu de înțeles",
      "compară produse din aceeași categorie după scor și nutrienți",
      "raportează recomandări greșite ca să îmbunătățim catalogul",
    ],
    categorySlugs: ["dulciuri", "snacks", "bauturi", "lactate", "produse-bio"],
  },
  {
    slug: "mega-image",
    storeId: "mega",
    name: "Mega Image",
    logo: "/stores/mega-image.png",
    tagline: "Cumpărături rapide, produse premium și multe decizii mici.",
    intro:
      "Pentru Mega Image, paginile Ce aleg? sunt gândite pentru cumpărături rapide: scanezi, vezi verdictul și verifici dacă alternativa merită.",
    shopperIntent: "bun pentru gustări, lactate, cafea, produse bio și mâncare rapidă",
    checks: [
      "verifică rapid produsele premium sau importate",
      "compară snacks și dulciuri după zahăr și ingrediente",
      "adaugă prețul observat pentru produse cumpărate des",
    ],
    categorySlugs: ["snacks", "lactate", "cafea", "produse-bio", "dulciuri"],
  },
  {
    slug: "profi",
    storeId: "profi",
    name: "Profi",
    logo: "/stores/profi.png",
    tagline: "Magazine apropiate, produse uzuale și decizii rapide.",
    intro:
      "În Profi, Ce aleg? ajută mai ales când vrei să verifici repede produse de bază sau gustări și să salvezi alternative pentru data viitoare.",
    shopperIntent: "bun pentru băuturi, dulciuri, panificație, mezeluri și produse de bază",
    checks: [
      "scanează produsele cumpărate des ca să ai istoric",
      "verifică diferențele între produse similare de raft",
      "contribuie cu produse locale sau promoții lipsă",
    ],
    categorySlugs: ["bauturi", "dulciuri", "panificatie", "mezeluri", "snacks"],
  },
  {
    slug: "penny",
    storeId: "penny",
    name: "Penny",
    logo: "/stores/penny.png",
    tagline: "Prețuri mici și produse de bază care merită verificate simplu.",
    intro:
      "Pentru Penny, Ce aleg? poate ajuta la comparații simple: produsul e bun pentru ce ai nevoie sau există o alternativă mai echilibrată?",
    shopperIntent: "bun pentru lactate, conserve, băuturi, dulciuri și produse de bază",
    checks: [
      "compară produsele ieftine după scor, nu doar după preț",
      "urmărește zahărul și ingredientele la gustări",
      "adaugă produse lipsă ca să ajuți catalogul pentru România",
    ],
    categorySlugs: ["lactate", "conserve", "bauturi", "dulciuri", "panificatie"],
  },
  {
    slug: "market-local",
    storeId: "local",
    name: "Market local",
    logo: "/stores/market-local.png",
    tagline: "Magazine independente, produse regionale și catalog completat de comunitate.",
    intro:
      "Produsele din magazine locale sunt cel mai greu de obținut de la retaileri, deci contribuțiile utilizatorilor sunt importante pentru un catalog românesc real.",
    shopperIntent: "bun pentru produse locale, mezeluri, panificație, lactate și conserve",
    checks: [
      "fotografiază ambalajul și tabelul nutrițional când produsul lipsește",
      "completează magazinul și categoria ca verificarea să fie mai rapidă",
      "ajută alți utilizatori din zona ta să găsească produsul",
    ],
    categorySlugs: ["mezeluri", "panificatie", "lactate", "conserve", "bauturi"],
  },
];

export const SEO_CATEGORIES = [
  {
    slug: "lactate",
    name: "Lactate",
    image: "/products/skyr.webp",
    intro:
      "Iaurturi, lapte, skyr, brânzeturi și deserturi lactate pot părea similare la raft, dar diferă mult la zahăr, proteină și lista de ingrediente.",
    examples: ["iaurt simplu", "skyr", "lapte", "brânză proaspătă", "desert lactat"],
    compareSignals: ["zahăr per 100g", "proteină", "grăsimi", "ingrediente simple"],
    advice:
      "Scanează codul de bare și compară produse din aceeași familie, mai ales când alegi pentru copii sau pentru gustări zilnice.",
    relatedStoreSlugs: ["lidl", "kaufland", "carrefour", "penny"],
  },
  {
    slug: "mezeluri",
    name: "Mezeluri",
    image: "/products/iaurt-grecesc.jpg",
    intro:
      "Mezelurile au diferențe mari la sare, procent de carne, aditivi și procesare. O verificare rapidă ajută când eticheta e încărcată.",
    examples: ["șuncă", "salam", "cârnați", "piept de pui feliat", "parizer"],
    compareSignals: ["procent carne", "sare", "aditivi", "grăsimi saturate"],
    advice:
      "Pentru mezeluri, catalogul crește cel mai bine din produse reale scanate la raft, fiindcă multe variante sunt specifice magazinului.",
    relatedStoreSlugs: ["kaufland", "profi", "market-local", "penny"],
  },
  {
    slug: "dulciuri",
    name: "Dulciuri",
    image: "/products/baton-ovaz.jpg",
    intro:
      "Batoane, biscuiți, ciocolată și deserturi ambalate sunt căutate des, dar unele au foarte mult zahăr pentru o porție mică.",
    examples: ["biscuiți", "ciocolată", "napolitane", "batoane", "deserturi ambalate"],
    compareSignals: ["zahăr", "calorii per porție", "grăsimi", "îndulcitori"],
    advice:
      "Scanează produsul și caută alternative apropiate dacă vrei o gustare mai echilibrată sau mai simplă.",
    relatedStoreSlugs: ["lidl", "carrefour", "mega-image", "profi"],
  },
  {
    slug: "snacks",
    name: "Snacks",
    image: "/products/baton-proteic.jpg",
    intro:
      "Snacks-urile pot fi rapide și convenabile, dar scorul depinde mult de zahăr, sare, proteină și cât de procesată este rețeta.",
    examples: ["chipsuri", "batoane proteice", "covrigei", "mixuri", "gustări sărate"],
    compareSignals: ["sare", "zahăr", "proteină", "calorii"],
    advice:
      "Folosește Ce aleg? când ai mai multe produse asemănătoare și vrei să alegi varianta care se potrivește mai bine obiectivului tău.",
    relatedStoreSlugs: ["lidl", "carrefour", "mega-image", "profi"],
  },
  {
    slug: "bauturi",
    name: "Băuturi",
    image: "/products/lapte-ovaz.jpg",
    intro:
      "Băuturile răcoritoare, vegetale sau funcționale pot ascunde zahăr, îndulcitori sau ingrediente greu de comparat rapid.",
    examples: ["sucuri", "băuturi vegetale", "energy drinks", "ceaiuri reci", "apă aromatizată"],
    compareSignals: ["zahăr per 100ml", "îndulcitori", "cofeină", "ingrediente"],
    advice:
      "Scanează mai ales băuturile cumpărate des, pentru că diferențele mici pe etichetă devin importante în consum repetat.",
    relatedStoreSlugs: ["lidl", "kaufland", "carrefour", "penny"],
  },
  {
    slug: "cereale",
    name: "Cereale",
    image: "/products/iaurt-simplu.jpg",
    intro:
      "Cerealele de mic dejun, granola și musli pot avea diferențe mari la zahăr și fibre, chiar dacă ambalajele par sănătoase.",
    examples: ["cereale mic dejun", "granola", "musli", "fulgi ovăz", "mixuri cu fructe"],
    compareSignals: ["zahăr", "fibre", "proteină", "lista ingredientelor"],
    advice:
      "Compară produsele per 100g și verifică dacă varianta aleasă se potrivește pentru mic dejun zilnic sau doar ocazional.",
    relatedStoreSlugs: ["lidl", "kaufland", "carrefour", "mega-image"],
  },
  {
    slug: "conserve",
    name: "Conserve",
    image: "/products/iaurt-grecesc.png",
    intro:
      "Conservele sunt practice, dar merită comparate după sare, ulei, ingrediente și raportul dintre produs și sos sau lichid.",
    examples: ["ton", "fasole", "năut", "roșii", "porumb"],
    compareSignals: ["sare", "ulei", "ingrediente", "cantitate netă"],
    advice:
      "Scanează conservele folosite des în rețete și salvează variantele cu etichetă mai clară.",
    relatedStoreSlugs: ["kaufland", "penny", "carrefour", "market-local"],
  },
  {
    slug: "panificatie",
    name: "Panificație",
    image: "/products/iaurt-natural-lidl.jpg",
    intro:
      "Pâinea ambalată, lipiile, crackersii și produsele de panificație diferă la fibre, sare și ingrediente adăugate.",
    examples: ["pâine ambalată", "lipii", "crackers", "chifle", "toast"],
    compareSignals: ["fibre", "sare", "zahăr", "făină folosită"],
    advice:
      "Pentru produse consumate zilnic, compară rapid eticheta și salvează alternativele care se potrivesc familiei.",
    relatedStoreSlugs: ["kaufland", "profi", "penny", "market-local"],
  },
  {
    slug: "produse-bio",
    name: "Produse bio",
    image: "/products/lapte-ovaz.jpg",
    intro:
      "Un produs bio nu este automat cea mai bună alegere pentru orice obiectiv. Eticheta și nutrienții rămân importanți.",
    examples: ["gustări bio", "băuturi vegetale", "cereale bio", "sosuri bio", "deserturi bio"],
    compareSignals: ["zahăr", "ingrediente", "calorii", "preț observat"],
    advice:
      "Scanează produsul și compară-l cu variante similare, nu doar după promisiunea de pe ambalaj.",
    relatedStoreSlugs: ["carrefour", "mega-image", "kaufland", "lidl"],
  },
  {
    slug: "cafea",
    name: "Cafea",
    image: "/products/baton-proteic.jpg",
    intro:
      "Cafeaua simplă, băuturile pe bază de cafea și produsele instant trebuie comparate diferit, mai ales când apar zahăr și arome.",
    examples: ["cafea măcinată", "capsule", "băuturi cafea", "instant", "mixuri 3 în 1"],
    compareSignals: ["zahăr", "ingrediente", "cofeină", "porție"],
    advice:
      "Scanează mixurile și băuturile ambalate cu cafea, unde eticheta poate fi mai importantă decât brandul.",
    relatedStoreSlugs: ["mega-image", "carrefour", "kaufland", "lidl"],
  },
];

export function getSeoStore(slug) {
  return SEO_STORES.find((store) => store.slug === slug) || null;
}

export function getSeoCategory(slug) {
  return SEO_CATEGORIES.find((category) => category.slug === slug) || null;
}

export function getStoresForCategory(category) {
  return (category.relatedStoreSlugs || [])
    .map(getSeoStore)
    .filter(Boolean);
}

export function getCategoriesForStore(store) {
  return (store.categorySlugs || [])
    .map(getSeoCategory)
    .filter(Boolean);
}

export const SEO_PRODUCTS = [
  {
    slug: "iaurt-grecesc-2",
    name: "Iaurt grecesc 2%",
    brand: "exemplu catalog",
    image: "/products/iaurt-grecesc.jpg",
    categorySlug: "lactate",
    storeSlugs: ["kaufland", "carrefour", "lidl"],
    score: "8.7",
    verdict: "Alegere bună pentru gustări simple, dacă ingredientele rămân scurte.",
    intro:
      "Iaurtul grecesc 2% este un exemplu bun de produs unde merită comparate proteina, zahărul și lista de ingrediente, nu doar ambalajul.",
    nutrients: ["proteină bună", "zahăr redus", "grăsimi moderate", "ingrediente simple"],
    goodFor: ["gustare rapidă", "mic dejun", "rețete simple"],
    watchOut: ["variante cu zahăr adăugat", "deserturi lactate confundate cu iaurt", "porții mai mari decât par"],
    alternativeSlugs: ["skyr-simplu", "iaurt-simplu", "iaurt-natural-lidl"],
  },
  {
    slug: "skyr-simplu",
    name: "Skyr simplu",
    brand: "exemplu catalog",
    image: "/products/skyr.webp",
    categorySlug: "lactate",
    storeSlugs: ["lidl", "kaufland", "carrefour"],
    score: "8.9",
    verdict: "Profil bun când vrei proteină mai mare și zahăr redus.",
    intro:
      "Skyr-ul simplu este căutat des ca alternativă la iaurturi dulci sau deserturi lactate, mai ales când obiectivul este proteina.",
    nutrients: ["proteină ridicată", "zahăr redus", "grăsimi scăzute", "fără topping dulce"],
    goodFor: ["gustări proteice", "mic dejun", "rețete cu fructe"],
    watchOut: ["variante cu arome", "toppinguri dulci", "preț per porție"],
    alternativeSlugs: ["iaurt-grecesc-2", "iaurt-simplu", "iaurt-proteic-lidl"],
  },
  {
    slug: "iaurt-natural-lidl",
    name: "Iaurt natural Lidl",
    brand: "exemplu Lidl",
    image: "/products/iaurt-natural-lidl.jpg",
    categorySlug: "lactate",
    storeSlugs: ["lidl"],
    score: "7.8",
    verdict: "O bază bună dacă eticheta rămâne simplă și zahărul este natural.",
    intro:
      "Un iaurt natural de magazin merită verificat rapid, pentru că produse similare pot avea ingrediente sau valori nutriționale diferite.",
    nutrients: ["ingrediente simple", "zahăr natural", "proteină medie", "preț accesibil"],
    goodFor: ["familie", "rețete", "cumpărături frecvente"],
    watchOut: ["iaurturi îndulcite", "ambalaje mari greu de comparat", "grăsime diferită"],
    alternativeSlugs: ["iaurt-simplu", "iaurt-grecesc-2", "skyr-simplu"],
  },
  {
    slug: "iaurt-proteic-lidl",
    name: "Iaurt proteic Lidl",
    brand: "exemplu Lidl",
    image: "/products/iaurt-proteic-lidl.jpg",
    categorySlug: "lactate",
    storeSlugs: ["lidl"],
    score: "8.2",
    verdict: "Interesant pentru proteină, dar merită verificați îndulcitorii și aromele.",
    intro:
      "Produsele proteice pot fi utile, însă nu toate au aceeași listă de ingrediente. Scanarea ajută când ai multe variante similare.",
    nutrients: ["proteină ridicată", "zahăr controlat", "calorii per porție", "ingrediente de verificat"],
    goodFor: ["după antrenament", "gustare sățioasă", "comparații rapide"],
    watchOut: ["îndulcitori", "arome", "promisiuni de marketing"],
    alternativeSlugs: ["skyr-simplu", "iaurt-grecesc-2", "iaurt-simplu"],
  },
  {
    slug: "iaurt-simplu",
    name: "Iaurt simplu",
    brand: "exemplu catalog",
    image: "/products/iaurt-simplu.jpg",
    categorySlug: "lactate",
    storeSlugs: ["kaufland", "penny", "market-local"],
    score: "7.9",
    verdict: "Alegere echilibrată când lista de ingrediente este clară.",
    intro:
      "Iaurtul simplu rămâne o categorie bună pentru comparații, mai ales când alegi des același produs pentru casă.",
    nutrients: ["zahăr natural", "proteină medie", "grăsimi variabile", "ingrediente scurte"],
    goodFor: ["mic dejun", "rețete", "gustări pentru familie"],
    watchOut: ["variante cu fructe și zahăr", "porții mari", "diferențe de grăsime"],
    alternativeSlugs: ["iaurt-grecesc-2", "skyr-simplu", "iaurt-natural-lidl"],
  },
  {
    slug: "bautura-ovaz",
    name: "Băutură de ovăz",
    brand: "exemplu catalog",
    image: "/products/lapte-ovaz.jpg",
    categorySlug: "bauturi",
    storeSlugs: ["lidl", "carrefour", "mega-image", "kaufland"],
    score: "6.8",
    verdict: "Poate fi potrivită, dar zahărul, uleiurile și aditivii merită verificați.",
    intro:
      "Băuturile vegetale par asemănătoare, însă pot diferi mult la zahăr, uleiuri, sare și adaosuri.",
    nutrients: ["zahăr per 100ml", "uleiuri", "sare", "fortifiere"],
    goodFor: ["cafea", "mic dejun", "alternative vegetale"],
    watchOut: ["zahăr adăugat", "uleiuri", "listă lungă de aditivi"],
    alternativeSlugs: ["iaurt-simplu", "skyr-simplu"],
  },
  {
    slug: "baton-proteic",
    name: "Baton proteic",
    brand: "exemplu catalog",
    image: "/products/baton-proteic.jpg",
    categorySlug: "snacks",
    storeSlugs: ["carrefour", "mega-image", "lidl"],
    score: "8.6",
    verdict: "Alternativă bună când proteina este reală și zahărul rămâne controlat.",
    intro:
      "Batoanele proteice sunt utile pentru comparații SEO, fiindcă multe produse promit mult, dar diferă la zahăr și ingrediente.",
    nutrients: ["proteină", "zahăr", "fibre", "calorii"],
    goodFor: ["gustare rapidă", "după sport", "alternative la dulciuri"],
    watchOut: ["zahăr alcool", "calorii ascunse", "preț per baton"],
    alternativeSlugs: ["baton-ovaz", "skyr-simplu", "iaurt-proteic-lidl"],
  },
  {
    slug: "baton-ovaz",
    name: "Baton de ovăz dulce",
    brand: "exemplu catalog",
    image: "/products/baton-ovaz.jpg",
    categorySlug: "dulciuri",
    storeSlugs: ["carrefour", "mega-image", "profi"],
    score: "3.4",
    verdict: "Gustare dulce de verificat atent, mai ales pentru zahăr și porție.",
    intro:
      "Un baton de ovăz poate părea o gustare sănătoasă, dar unele variante au mult zahăr pentru o porție mică.",
    nutrients: ["zahăr ridicat", "calorii", "fibre", "ingrediente"],
    goodFor: ["ocazional", "energie rapidă"],
    watchOut: ["zahăr pe porție", "glazuri", "porții mici, dar calorice"],
    alternativeSlugs: ["baton-proteic", "skyr-simplu", "iaurt-grecesc-2"],
  },
];

export const SEO_ALTERNATIVE_GUIDES = [
  {
    slug: "iaurturi",
    title: "Alternative la iaurturi dulci",
    image: "/products/skyr.webp",
    intro:
      "Când un iaurt pare sănătos, verifică zahărul, proteina și ingredientele. Alternativele bune sunt adesea iaurtul simplu, skyr-ul sau iaurtul grecesc.",
    categorySlugs: ["lactate"],
    productSlugs: ["baton-ovaz", "iaurt-grecesc-2", "skyr-simplu", "iaurt-simplu"],
    checks: ["zahăr per 100g", "proteină", "ingrediente scurte", "fără topping dulce"],
    searchIntent: "pentru oameni care caută iaurturi mai bune, mai simple sau mai proteice",
  },
  {
    slug: "dulciuri",
    title: "Alternative la dulciuri foarte zaharoase",
    image: "/products/baton-ovaz.jpg",
    intro:
      "Nu toate gustările dulci sunt la fel. Unele pot fi înlocuite cu variante mai sățioase sau cu zahăr mai controlat.",
    categorySlugs: ["dulciuri", "snacks"],
    productSlugs: ["baton-ovaz", "baton-proteic", "skyr-simplu"],
    checks: ["zahăr", "calorii per porție", "fibre", "proteină"],
    searchIntent: "pentru căutări despre dulciuri mai ok și gustări alternative",
  },
  {
    slug: "bauturi",
    title: "Alternative la băuturi cu zahăr",
    image: "/products/lapte-ovaz.jpg",
    intro:
      "Băuturile pot adăuga zahăr fără să pară o masă. Compară valorile per 100ml și verifică îndulcitorii sau ingredientele.",
    categorySlugs: ["bauturi", "produse-bio"],
    productSlugs: ["bautura-ovaz", "iaurt-simplu", "skyr-simplu"],
    checks: ["zahăr per 100ml", "îndulcitori", "cofeină", "ingrediente"],
    searchIntent: "pentru oameni care vor băuturi mai simple sau mai ușor de comparat",
  },
  {
    slug: "snacks",
    title: "Alternative la snacks-uri sărate sau dulci",
    image: "/products/baton-proteic.jpg",
    intro:
      "La snacks contează mult porția, sarea, zahărul și cât de sățios este produsul. Scanarea te ajută să compari variante similare.",
    categorySlugs: ["snacks", "dulciuri"],
    productSlugs: ["baton-proteic", "baton-ovaz", "iaurt-grecesc-2"],
    checks: ["sare", "zahăr", "proteină", "calorii"],
    searchIntent: "pentru căutări despre gustări mai bune și alternative la raft",
  },
  {
    slug: "mezeluri",
    title: "Alternative la mezeluri foarte procesate",
    image: "/stores/market-local.png",
    intro:
      "Mezelurile sunt o categorie unde catalogul are nevoie de contribuții reale: procent de carne, sare, aditivi și ingrediente.",
    categorySlugs: ["mezeluri"],
    productSlugs: ["iaurt-grecesc-2", "skyr-simplu"],
    checks: ["procent carne", "sare", "aditivi", "grăsimi"],
    searchIntent: "pentru căutări despre mezeluri mai simple și produse mai puțin procesate",
  },
  {
    slug: "cereale-mic-dejun",
    title: "Alternative la cereale de mic dejun cu mult zahăr",
    image: "/products/iaurt-simplu.jpg",
    intro:
      "Cerealele pot părea potrivite pentru mic dejun, dar zahărul și fibrele schimbă mult verdictul.",
    categorySlugs: ["cereale", "lactate"],
    productSlugs: ["iaurt-simplu", "skyr-simplu", "iaurt-grecesc-2"],
    checks: ["zahăr", "fibre", "proteină", "ingrediente"],
    searchIntent: "pentru căutări despre mic dejun mai simplu și produse pentru familie",
  },
];

export function getSeoProduct(slug) {
  return SEO_PRODUCTS.find((product) => product.slug === slug) || null;
}

export function getSeoAlternativeGuide(slug) {
  return SEO_ALTERNATIVE_GUIDES.find((guide) => guide.slug === slug) || null;
}

export function getProductsForCategory(categorySlug) {
  return SEO_PRODUCTS.filter((product) => product.categorySlug === categorySlug);
}

export function getProductsForStore(storeSlug) {
  return SEO_PRODUCTS.filter((product) => product.storeSlugs.includes(storeSlug));
}

export function getProductsForAlternativeGuide(guide) {
  return (guide.productSlugs || [])
    .map(getSeoProduct)
    .filter(Boolean);
}

export function getCategoriesForAlternativeGuide(guide) {
  return (guide.categorySlugs || [])
    .map(getSeoCategory)
    .filter(Boolean);
}

export function getAlternativesForProduct(product) {
  return (product.alternativeSlugs || [])
    .map(getSeoProduct)
    .filter(Boolean);
}

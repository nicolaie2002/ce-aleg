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

const STORE_COPY_EN = {
  lidl: {
    tagline: "Everyday products, many private labels and prices worth comparing.",
    intro:
      "This page helps people looking for Lidl products in Romania understand how to scan barcodes, compare labels and contribute missing products to the Ce aleg? catalog.",
    shopperIntent: "good for dairy, snacks, sweets, drinks and pantry basics",
    checks: [
      "compare sugar in yogurts, cereals and snacks",
      "check protein and ingredients in high-protein products",
      "add missing products when you scan a new barcode",
    ],
  },
  kaufland: {
    tagline: "Large baskets, many categories and close shelf alternatives.",
    intro:
      "For Kaufland, Ce aleg? works as a quick scanning assistant when you have many similar products and want the clearer option.",
    shopperIntent: "good for dairy, canned foods, bakery, drinks and family products",
    checks: [
      "scan similar products before choosing bulk or large formats",
      "watch the score, sugar, salt and important ingredients",
      "submit products that are missing from the catalog",
    ],
  },
  carrefour: {
    tagline: "Many brands and similar products, useful for fast comparisons.",
    intro:
      "In Carrefour you can use Ce aleg? to compare products close in price or category and find alternatives that fit your preferences.",
    shopperIntent: "good for sweets, snacks, drinks, dairy and organic products",
    checks: [
      "look for alternatives when the label is hard to understand",
      "compare products in the same category by score and nutrients",
      "report wrong recommendations so we can improve the catalog",
    ],
  },
  "mega-image": {
    tagline: "Quick shopping, premium products and many small decisions.",
    intro:
      "For Mega Image, Ce aleg? pages are built for quick shopping: scan, see the verdict and check whether the alternative is worth it.",
    shopperIntent: "good for snacks, dairy, coffee, organic products and quick meals",
    checks: [
      "quickly check premium or imported products",
      "compare snacks and sweets by sugar and ingredients",
      "add the observed price for products you buy often",
    ],
  },
  profi: {
    tagline: "Nearby stores, everyday products and quick decisions.",
    intro:
      "In Profi, Ce aleg? helps especially when you want to quickly check basic products or snacks and save alternatives for next time.",
    shopperIntent: "good for drinks, sweets, bakery, deli meats and basics",
    checks: [
      "scan products you buy often so you keep a useful history",
      "check differences between similar shelf products",
      "contribute local or promotional products that are missing",
    ],
  },
  penny: {
    tagline: "Low prices and basic products that are worth checking simply.",
    intro:
      "For Penny, Ce aleg? helps with simple comparisons: is the product right for what you need, or is there a more balanced alternative?",
    shopperIntent: "good for dairy, canned foods, drinks, sweets and basics",
    checks: [
      "compare cheap products by score, not only by price",
      "watch sugar and ingredients in snacks",
      "add missing products to help the Romanian catalog",
    ],
  },
  "market-local": {
    tagline: "Independent shops, regional products and a community-built catalog.",
    intro:
      "Products from local shops are the hardest to obtain from retailers, so user contributions matter for a real Romanian catalog.",
    shopperIntent: "good for local products, deli meats, bakery, dairy and canned foods",
    checks: [
      "photograph the package and nutrition table when a product is missing",
      "complete the store and category so review is faster",
      "help other people nearby find the product",
    ],
  },
};

const CATEGORY_COPY_EN = {
  lactate: {
    name: "Dairy",
    intro:
      "Yogurts, milk, skyr, cheeses and dairy desserts can look similar on the shelf, but differ a lot in sugar, protein and ingredients.",
    examples: ["plain yogurt", "skyr", "milk", "fresh cheese", "dairy dessert"],
    compareSignals: ["sugar per 100g", "protein", "fat", "simple ingredients"],
    advice:
      "Scan the barcode and compare products from the same family, especially when choosing for children or daily snacks.",
  },
  mezeluri: {
    name: "Deli meats",
    intro:
      "Deli meats vary widely in salt, meat percentage, additives and processing. A quick check helps when the label is crowded.",
    examples: ["ham", "salami", "sausages", "sliced chicken breast", "bologna"],
    compareSignals: ["meat percentage", "salt", "additives", "saturated fat"],
    advice:
      "For deli meats, the catalog grows best from real shelf scans because many variants are store-specific.",
  },
  dulciuri: {
    name: "Sweets",
    intro:
      "Bars, biscuits, chocolate and packaged desserts are searched often, but some contain a lot of sugar for a small portion.",
    examples: ["biscuits", "chocolate", "wafers", "bars", "packaged desserts"],
    compareSignals: ["sugar", "calories per portion", "fat", "sweeteners"],
    advice:
      "Scan the product and look for nearby alternatives if you want a more balanced or simpler snack.",
  },
  snacks: {
    name: "Snacks",
    intro:
      "Snacks can be quick and convenient, but the score depends a lot on sugar, salt, protein and how processed the recipe is.",
    examples: ["chips", "protein bars", "pretzels", "mixes", "salty snacks"],
    compareSignals: ["salt", "sugar", "protein", "calories"],
    advice:
      "Use Ce aleg? when you have several similar products and want the one that fits your goal better.",
  },
  bauturi: {
    name: "Drinks",
    intro:
      "Soft, plant-based or functional drinks can hide sugar, sweeteners or ingredients that are hard to compare quickly.",
    examples: ["juices", "plant-based drinks", "energy drinks", "iced teas", "flavored water"],
    compareSignals: ["sugar per 100ml", "sweeteners", "caffeine", "ingredients"],
    advice:
      "Scan drinks you buy often, because small label differences matter when consumption is repeated.",
  },
  cereale: {
    name: "Cereals",
    intro:
      "Breakfast cereals, granola and muesli can vary a lot in sugar and fiber even when the packaging looks healthy.",
    examples: ["breakfast cereal", "granola", "muesli", "oat flakes", "fruit mixes"],
    compareSignals: ["sugar", "fiber", "protein", "ingredient list"],
    advice:
      "Compare products per 100g and check whether the chosen option fits a daily breakfast or only an occasional one.",
  },
  conserve: {
    name: "Canned foods",
    intro:
      "Canned foods are practical, but worth comparing by salt, oil, ingredients and the ratio between product and sauce or liquid.",
    examples: ["tuna", "beans", "chickpeas", "tomatoes", "corn"],
    compareSignals: ["salt", "oil", "ingredients", "net quantity"],
    advice:
      "Scan canned foods you use often in recipes and save the options with a clearer label.",
  },
  panificatie: {
    name: "Bakery",
    intro:
      "Packaged bread, wraps, crackers and bakery products differ in fiber, salt and added ingredients.",
    examples: ["packaged bread", "wraps", "crackers", "buns", "toast"],
    compareSignals: ["fiber", "salt", "sugar", "flour type"],
    advice:
      "For products eaten daily, compare the label quickly and save the alternatives that fit your family.",
  },
  "produse-bio": {
    name: "Organic products",
    intro:
      "An organic product is not automatically the best choice for every goal. The label and nutrients still matter.",
    examples: ["organic snacks", "plant-based drinks", "organic cereals", "organic sauces", "organic desserts"],
    compareSignals: ["sugar", "ingredients", "calories", "observed price"],
    advice:
      "Scan the product and compare it with similar options, not only by the promise on the package.",
  },
  cafea: {
    name: "Coffee",
    intro:
      "Plain coffee, coffee-based drinks and instant products should be compared differently, especially when sugar and flavors appear.",
    examples: ["ground coffee", "capsules", "coffee drinks", "instant", "3-in-1 mixes"],
    compareSignals: ["sugar", "ingredients", "caffeine", "portion"],
    advice:
      "Scan packaged coffee mixes and drinks, where the label can matter more than the brand.",
  },
};

const PRODUCT_COPY_EN = {
  "iaurt-grecesc-2": {
    name: "Greek yogurt 2%",
    brand: "catalog example",
    verdict: "Good choice for simple snacks if the ingredient list stays short.",
    intro:
      "Greek yogurt 2% is a good example of a product where protein, sugar and ingredients are worth comparing, not only the packaging.",
    nutrients: ["good protein", "low sugar", "moderate fat", "simple ingredients"],
    goodFor: ["quick snack", "breakfast", "simple recipes"],
    watchOut: ["versions with added sugar", "dairy desserts confused with yogurt", "portions larger than they look"],
  },
  "skyr-simplu": {
    name: "Plain skyr",
    brand: "catalog example",
    verdict: "Good profile when you want higher protein and lower sugar.",
    intro:
      "Plain skyr is often searched as an alternative to sweet yogurts or dairy desserts, especially when the goal is protein.",
    nutrients: ["high protein", "low sugar", "low fat", "no sweet topping"],
    goodFor: ["protein snacks", "breakfast", "fruit recipes"],
    watchOut: ["flavored versions", "sweet toppings", "price per portion"],
  },
  "iaurt-natural-lidl": {
    name: "Lidl plain yogurt",
    brand: "Lidl example",
    verdict: "A good base if the label stays simple and the sugar is natural.",
    intro:
      "A store-brand plain yogurt is worth checking quickly because similar products can have different ingredients or nutrition values.",
    nutrients: ["simple ingredients", "natural sugar", "medium protein", "accessible price"],
    goodFor: ["family", "recipes", "frequent shopping"],
    watchOut: ["sweetened yogurts", "large packages that are hard to compare", "different fat levels"],
  },
  "iaurt-proteic-lidl": {
    name: "Lidl protein yogurt",
    brand: "Lidl example",
    verdict: "Interesting for protein, but sweeteners and flavors are worth checking.",
    intro:
      "Protein products can be useful, but they do not all have the same ingredient list. Scanning helps when many variants look similar.",
    nutrients: ["high protein", "controlled sugar", "calories per portion", "ingredients to check"],
    goodFor: ["after training", "filling snack", "quick comparisons"],
    watchOut: ["sweeteners", "flavors", "marketing promises"],
  },
  "iaurt-simplu": {
    name: "Plain yogurt",
    brand: "catalog example",
    verdict: "Balanced choice when the ingredient list is clear.",
    intro:
      "Plain yogurt remains a useful category for comparisons, especially when you often choose the same product for home.",
    nutrients: ["natural sugar", "medium protein", "variable fat", "short ingredients"],
    goodFor: ["breakfast", "recipes", "family snacks"],
    watchOut: ["fruit and sugar versions", "large portions", "fat differences"],
  },
  "bautura-ovaz": {
    name: "Oat drink",
    brand: "catalog example",
    verdict: "May fit well, but sugar, oils and additives are worth checking.",
    intro:
      "Plant-based drinks look similar, but can differ a lot in sugar, oils, salt and additions.",
    nutrients: ["sugar per 100ml", "oils", "salt", "fortification"],
    goodFor: ["coffee", "breakfast", "plant-based alternatives"],
    watchOut: ["added sugar", "oils", "long additive list"],
  },
  "baton-proteic": {
    name: "Protein bar",
    brand: "catalog example",
    verdict: "Good alternative when protein is real and sugar stays controlled.",
    intro:
      "Protein bars are useful for comparisons because many products promise a lot, but differ in sugar and ingredients.",
    nutrients: ["protein", "sugar", "fiber", "calories"],
    goodFor: ["quick snack", "after sport", "alternatives to sweets"],
    watchOut: ["sugar alcohols", "hidden calories", "price per bar"],
  },
  "baton-ovaz": {
    name: "Sweet oat bar",
    brand: "catalog example",
    verdict: "Sweet snack to check carefully, especially for sugar and portion size.",
    intro:
      "An oat bar may look like a healthy snack, but some versions contain a lot of sugar for a small portion.",
    nutrients: ["high sugar", "calories", "fiber", "ingredients"],
    goodFor: ["occasional", "quick energy"],
    watchOut: ["sugar per portion", "glazes", "small but calorie-dense portions"],
  },
};

const ALTERNATIVE_GUIDE_COPY_EN = {
  iaurturi: {
    title: "Alternatives to sweet yogurts",
    intro:
      "When a yogurt looks healthy, check sugar, protein and ingredients. Good alternatives are often plain yogurt, skyr or Greek yogurt.",
    checks: ["sugar per 100g", "protein", "short ingredients", "no sweet topping"],
    searchIntent: "for people looking for better, simpler or higher-protein yogurts",
  },
  dulciuri: {
    title: "Alternatives to very sugary sweets",
    intro:
      "Not all sweet snacks are the same. Some can be replaced with more filling options or products with more controlled sugar.",
    checks: ["sugar", "calories per portion", "fiber", "protein"],
    searchIntent: "for searches about better sweets and alternative snacks",
  },
  bauturi: {
    title: "Alternatives to sugary drinks",
    intro:
      "Drinks can add sugar without feeling like a meal. Compare values per 100ml and check sweeteners or ingredients.",
    checks: ["sugar per 100ml", "sweeteners", "caffeine", "ingredients"],
    searchIntent: "for people who want simpler drinks that are easier to compare",
  },
  snacks: {
    title: "Alternatives to salty or sweet snacks",
    intro:
      "For snacks, portion, salt, sugar and satiety matter a lot. Scanning helps you compare similar shelf options.",
    checks: ["salt", "sugar", "protein", "calories"],
    searchIntent: "for searches about better snacks and shelf alternatives",
  },
  mezeluri: {
    title: "Alternatives to highly processed deli meats",
    intro:
      "Deli meats are a category where the catalog needs real contributions: meat percentage, salt, additives and ingredients.",
    checks: ["meat percentage", "salt", "additives", "fat"],
    searchIntent: "for searches about simpler deli meats and less processed products",
  },
  "cereale-mic-dejun": {
    title: "Alternatives to high-sugar breakfast cereals",
    intro:
      "Cereals can look suitable for breakfast, but sugar and fiber change the verdict a lot.",
    checks: ["sugar", "fiber", "protein", "ingredients"],
    searchIntent: "for searches about simpler breakfasts and family products",
  },
};

const CATALOG_LABEL_EN_BY_KEY = {
  altele: "Other",
  carne: "Meat",
  sucuri: "Juices",
  apa: "Water",
  "bauturi racoritoare": "Soft drinks",
  "lactate si branzeturi": "Dairy and cheese",
  lactate: "Dairy",
  "fructe si legume": "Fruit and vegetables",
  mezeluri: "Deli meats",
  dulciuri: "Sweets",
  snacks: "Snacks",
  bauturi: "Drinks",
  cereale: "Cereals",
  conserve: "Canned foods",
  panificatie: "Bakery",
  cafea: "Coffee",
  "produse bio": "Organic products",
};

function normalizeCatalogLabel(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

export function localizeCatalogLabel(value, locale) {
  if (locale !== "en") return value;
  return CATALOG_LABEL_EN_BY_KEY[normalizeCatalogLabel(value)] || value;
}

function localizeSeoItem(item, copyBySlug, locale) {
  if (locale !== "en" || !item) return item;
  return { ...item, ...(copyBySlug[item.slug] || {}) };
}

export function getLocalizedSeoStore(store, locale) {
  return localizeSeoItem(store, STORE_COPY_EN, locale);
}

export function getLocalizedSeoCategory(category, locale) {
  return localizeSeoItem(category, CATEGORY_COPY_EN, locale);
}

export function getLocalizedSeoProduct(product, locale) {
  return localizeSeoItem(product, PRODUCT_COPY_EN, locale);
}

export function getLocalizedSeoAlternativeGuide(guide, locale) {
  return localizeSeoItem(guide, ALTERNATIVE_GUIDE_COPY_EN, locale);
}

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

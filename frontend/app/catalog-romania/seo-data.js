export const CATALOG_SEO_SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop"
).replace(/\/$/, "");

export const SEO_STORES = [
  {
    slug: "lidl",
    storeId: "lidl",
    name: "Lidl",
    logo: "/stores/lidl.png",
    tagline: "Produse de zi cu zi, multe marci proprii si preturi care merita comparate.",
    intro:
      "Pagina ajuta utilizatorii care cauta produse Lidl in Romania sa inteleaga cum pot scana codul de bare, compara eticheta si contribui cu produse lipsa in catalogul Ce aleg?.",
    shopperIntent: "bun pentru lactate, snacks, dulciuri, bauturi si produse de baza",
    checks: [
      "compara zaharul la iaurturi, cereale si gustari",
      "verifica proteina si ingredientele la produse proteice",
      "adauga produse lipsa cand scanezi un cod nou",
    ],
    categorySlugs: ["lactate", "dulciuri", "snacks", "bauturi", "cereale"],
  },
  {
    slug: "kaufland",
    storeId: "kaufland",
    name: "Kaufland",
    logo: "/stores/kaufland.png",
    tagline: "Cosuri mari, multe categorii si alternative apropiate la raft.",
    intro:
      "Pentru Kaufland, Ce aleg? poate fi folosit ca asistent rapid de scanare cand ai multe produse similare si vrei sa alegi varianta mai potrivita.",
    shopperIntent: "bun pentru lactate, conserve, panificatie, bauturi si produse pentru familie",
    checks: [
      "scaneaza produse similare inainte sa alegi baxul sau formatul mare",
      "urmareste scorul, zaharul, sarea si ingredientele importante",
      "trimite la verificare produsele care lipsesc din catalog",
    ],
    categorySlugs: ["lactate", "conserve", "panificatie", "bauturi", "mezeluri"],
  },
  {
    slug: "carrefour",
    storeId: "carrefour",
    name: "Carrefour",
    logo: "/stores/carrefour.png",
    tagline: "Multe branduri si produse similare, potrivite pentru comparatii rapide.",
    intro:
      "In Carrefour poti folosi Ce aleg? ca sa compari produse apropiate ca pret sau categorie si sa gasesti alternative mai clare pentru preferintele tale.",
    shopperIntent: "bun pentru dulciuri, snacks, bauturi, lactate si produse bio",
    checks: [
      "cauta alternative cand eticheta pare greu de inteles",
      "compara produse din aceeasi categorie dupa scor si nutrienti",
      "raporteaza recomandari gresite ca sa imbunatatim catalogul",
    ],
    categorySlugs: ["dulciuri", "snacks", "bauturi", "lactate", "produse-bio"],
  },
  {
    slug: "mega-image",
    storeId: "mega",
    name: "Mega Image",
    logo: "/stores/mega-image.png",
    tagline: "Cumparaturi rapide, produse premium si multe decizii mici.",
    intro:
      "Pentru Mega Image, paginile Ce aleg? sunt gandite pentru cumparaturi rapide: scanezi, vezi verdictul si verifici daca alternativa merita.",
    shopperIntent: "bun pentru gustari, lactate, cafea, produse bio si mancare rapida",
    checks: [
      "verifica rapid produsele premium sau importate",
      "compara snacks si dulciuri dupa zahar si ingrediente",
      "adauga pretul observat pentru produse cumparate des",
    ],
    categorySlugs: ["snacks", "lactate", "cafea", "produse-bio", "dulciuri"],
  },
  {
    slug: "profi",
    storeId: "profi",
    name: "Profi",
    logo: "/stores/profi.png",
    tagline: "Magazine apropiate, produse uzuale si decizii rapide.",
    intro:
      "In Profi, Ce aleg? ajuta mai ales cand vrei sa verifici repede produse de baza sau gustari si sa salvezi alternative pentru data viitoare.",
    shopperIntent: "bun pentru bauturi, dulciuri, panificatie, mezeluri si produse de baza",
    checks: [
      "scaneaza produsele cumparate des ca sa ai istoric",
      "verifica diferentele intre produse similare de raft",
      "contribuie cu produse locale sau promotii lipsa",
    ],
    categorySlugs: ["bauturi", "dulciuri", "panificatie", "mezeluri", "snacks"],
  },
  {
    slug: "penny",
    storeId: "penny",
    name: "Penny",
    logo: "/stores/penny.png",
    tagline: "Preturi mici si produse de baza care merita verificate simplu.",
    intro:
      "Pentru Penny, Ce aleg? poate ajuta la comparatii simple: produsul e bun pentru ce ai nevoie sau exista o alternativa mai echilibrata?",
    shopperIntent: "bun pentru lactate, conserve, bauturi, dulciuri si produse de baza",
    checks: [
      "compara produsele ieftine dupa scor, nu doar dupa pret",
      "urmareste zaharul si ingredientele la gustari",
      "adauga produse lipsa ca sa ajuti catalogul pentru Romania",
    ],
    categorySlugs: ["lactate", "conserve", "bauturi", "dulciuri", "panificatie"],
  },
  {
    slug: "market-local",
    storeId: "local",
    name: "Market local",
    logo: "/stores/market-local.png",
    tagline: "Magazine independente, produse regionale si catalog completat de comunitate.",
    intro:
      "Produsele din magazine locale sunt cel mai greu de obtinut de la retaileri, deci contributiile utilizatorilor sunt importante pentru un catalog romanesc real.",
    shopperIntent: "bun pentru produse locale, mezeluri, panificatie, lactate si conserve",
    checks: [
      "fotografiaza ambalajul si tabelul nutritional cand produsul lipseste",
      "completeaza magazinul si categoria ca verificarea sa fie mai rapida",
      "ajuta alti utilizatori din zona ta sa gaseasca produsul",
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
      "Iaurturi, lapte, skyr, branzeturi si deserturi lactate pot parea similare la raft, dar difera mult la zahar, proteina si lista de ingrediente.",
    examples: ["iaurt simplu", "skyr", "lapte", "branza proaspata", "desert lactat"],
    compareSignals: ["zahar per 100g", "proteina", "grasimi", "ingrediente simple"],
    advice:
      "Scaneaza codul de bare si compara produse din aceeasi familie, mai ales cand alegi pentru copii sau pentru gustari zilnice.",
    relatedStoreSlugs: ["lidl", "kaufland", "carrefour", "penny"],
  },
  {
    slug: "mezeluri",
    name: "Mezeluri",
    image: "/products/iaurt-grecesc.jpg",
    intro:
      "Mezelurile au diferente mari la sare, procent de carne, aditivi si procesare. O verificare rapida ajuta cand eticheta e incarcata.",
    examples: ["sunca", "salam", "carnati", "piept de pui feliat", "parizer"],
    compareSignals: ["procent carne", "sare", "aditivi", "grasimi saturate"],
    advice:
      "Pentru mezeluri, catalogul creste cel mai bine din produse reale scanate la raft, fiindca multe variante sunt specifice magazinului.",
    relatedStoreSlugs: ["kaufland", "profi", "market-local", "penny"],
  },
  {
    slug: "dulciuri",
    name: "Dulciuri",
    image: "/products/baton-ovaz.jpg",
    intro:
      "Batoane, biscuiti, ciocolata si deserturi ambalate sunt cautate des, dar unele au foarte mult zahar pentru o portie mica.",
    examples: ["biscuiti", "ciocolata", "napolitane", "batoane", "deserturi ambalate"],
    compareSignals: ["zahar", "calorii per portie", "grasimi", "indulcitori"],
    advice:
      "Scaneaza produsul si cauta alternative apropiate daca vrei o gustare mai echilibrata sau mai simpla.",
    relatedStoreSlugs: ["lidl", "carrefour", "mega-image", "profi"],
  },
  {
    slug: "snacks",
    name: "Snacks",
    image: "/products/baton-proteic.jpg",
    intro:
      "Snacks-urile pot fi rapide si convenabile, dar scorul depinde mult de zahar, sare, proteina si cat de procesata este reteta.",
    examples: ["chipsuri", "batoane proteice", "covrigei", "mixuri", "gustari sarate"],
    compareSignals: ["sare", "zahar", "proteina", "calorii"],
    advice:
      "Foloseste Ce aleg? cand ai mai multe produse asemanatoare si vrei sa alegi varianta care se potriveste mai bine obiectivului tau.",
    relatedStoreSlugs: ["lidl", "carrefour", "mega-image", "profi"],
  },
  {
    slug: "bauturi",
    name: "Bauturi",
    image: "/products/lapte-ovaz.jpg",
    intro:
      "Bauturile racoritoare, vegetale sau functionale pot ascunde zahar, indulcitori sau ingrediente greu de comparat rapid.",
    examples: ["sucuri", "bauturi vegetale", "energy drinks", "ceaiuri reci", "apa aromatizata"],
    compareSignals: ["zahar per 100ml", "indulcitori", "cofeina", "ingrediente"],
    advice:
      "Scaneaza mai ales bauturile cumparate des, pentru ca diferentele mici pe eticheta devin importante in consum repetat.",
    relatedStoreSlugs: ["lidl", "kaufland", "carrefour", "penny"],
  },
  {
    slug: "cereale",
    name: "Cereale",
    image: "/products/iaurt-simplu.jpg",
    intro:
      "Cerealele de mic dejun, granola si musli pot avea diferente mari la zahar si fibre, chiar daca ambalajele par sanatoase.",
    examples: ["cereale mic dejun", "granola", "musli", "fulgi ovaz", "mixuri cu fructe"],
    compareSignals: ["zahar", "fibre", "proteina", "lista ingredientelor"],
    advice:
      "Compara produsele per 100g si verifica daca varianta aleasa se potriveste pentru mic dejun zilnic sau doar ocazional.",
    relatedStoreSlugs: ["lidl", "kaufland", "carrefour", "mega-image"],
  },
  {
    slug: "conserve",
    name: "Conserve",
    image: "/products/iaurt-grecesc.png",
    intro:
      "Conservele sunt practice, dar merita comparate dupa sare, ulei, ingrediente si raportul dintre produs si sos sau lichid.",
    examples: ["ton", "fasole", "naut", "rosii", "porumb"],
    compareSignals: ["sare", "ulei", "ingrediente", "cantitate neta"],
    advice:
      "Scaneaza conservele folosite des in retete si salveaza variantele cu eticheta mai clara.",
    relatedStoreSlugs: ["kaufland", "penny", "carrefour", "market-local"],
  },
  {
    slug: "panificatie",
    name: "Panificatie",
    image: "/products/iaurt-natural-lidl.jpg",
    intro:
      "Painea ambalata, lipiile, crackersii si produsele de panificatie difera la fibre, sare si ingrediente adaugate.",
    examples: ["paine ambalata", "lipii", "crackers", "chifle", "toast"],
    compareSignals: ["fibre", "sare", "zahar", "faina folosita"],
    advice:
      "Pentru produse consumate zilnic, compara rapid eticheta si salveaza alternativele care se potrivesc familiei.",
    relatedStoreSlugs: ["kaufland", "profi", "penny", "market-local"],
  },
  {
    slug: "produse-bio",
    name: "Produse bio",
    image: "/products/lapte-ovaz.jpg",
    intro:
      "Un produs bio nu este automat cea mai buna alegere pentru orice obiectiv. Eticheta si nutrientii raman importanti.",
    examples: ["gustari bio", "bauturi vegetale", "cereale bio", "sosuri bio", "deserturi bio"],
    compareSignals: ["zahar", "ingrediente", "calorii", "pret observat"],
    advice:
      "Scaneaza produsul si compara-l cu variante similare, nu doar dupa promisiunea de pe ambalaj.",
    relatedStoreSlugs: ["carrefour", "mega-image", "kaufland", "lidl"],
  },
  {
    slug: "cafea",
    name: "Cafea",
    image: "/products/baton-proteic.jpg",
    intro:
      "Cafeaua simpla, bauturile pe baza de cafea si produsele instant trebuie comparate diferit, mai ales cand apar zahar si arome.",
    examples: ["cafea macinata", "capsule", "bauturi cafea", "instant", "mixuri 3 in 1"],
    compareSignals: ["zahar", "ingrediente", "cofeina", "portie"],
    advice:
      "Scaneaza mixurile si bauturile ambalate cu cafea, unde eticheta poate fi mai importanta decat brandul.",
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
    verdict: "Alegere buna pentru gustari simple, daca ingredientele raman scurte.",
    intro:
      "Iaurtul grecesc 2% este un exemplu bun de produs unde merita comparate proteina, zaharul si lista de ingrediente, nu doar ambalajul.",
    nutrients: ["proteina buna", "zahar redus", "grasimi moderate", "ingrediente simple"],
    goodFor: ["gustare rapida", "mic dejun", "retete simple"],
    watchOut: ["variante cu zahar adaugat", "deserturi lactate confundate cu iaurt", "portii mai mari decat par"],
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
    verdict: "Profil bun cand vrei proteina mai mare si zahar redus.",
    intro:
      "Skyr-ul simplu este cautat des ca alternativa la iaurturi dulci sau deserturi lactate, mai ales cand obiectivul este proteina.",
    nutrients: ["proteina ridicata", "zahar redus", "grasimi scazute", "fara topping dulce"],
    goodFor: ["gustari proteice", "mic dejun", "retete cu fructe"],
    watchOut: ["variante cu arome", "toppinguri dulci", "pret per portie"],
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
    verdict: "O baza buna daca eticheta ramane simpla si zaharul este natural.",
    intro:
      "Un iaurt natural de magazin merita verificat rapid, pentru ca produse similare pot avea ingrediente sau valori nutritionale diferite.",
    nutrients: ["ingrediente simple", "zahar natural", "proteina medie", "pret accesibil"],
    goodFor: ["familie", "retete", "cumparaturi frecvente"],
    watchOut: ["iaurturi indulcite", "ambalaje mari greu de comparat", "grasime diferita"],
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
    verdict: "Interesant pentru proteina, dar merita verificati indulcitorii si aromele.",
    intro:
      "Produsele proteice pot fi utile, insa nu toate au aceeasi lista de ingrediente. Scanarea ajuta cand ai multe variante similare.",
    nutrients: ["proteina ridicata", "zahar controlat", "calorii per portie", "ingrediente de verificat"],
    goodFor: ["dupa antrenament", "gustare satioasa", "comparatii rapide"],
    watchOut: ["indulcitori", "arome", "promisiuni de marketing"],
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
    verdict: "Alegere echilibrata cand lista de ingrediente este clara.",
    intro:
      "Iaurtul simplu ramane o categorie buna pentru comparatii, mai ales cand alegi des acelasi produs pentru casa.",
    nutrients: ["zahar natural", "proteina medie", "grasimi variabile", "ingrediente scurte"],
    goodFor: ["mic dejun", "retete", "gustari pentru familie"],
    watchOut: ["variante cu fructe si zahar", "portii mari", "diferente de grasime"],
    alternativeSlugs: ["iaurt-grecesc-2", "skyr-simplu", "iaurt-natural-lidl"],
  },
  {
    slug: "bautura-ovaz",
    name: "Bautura de ovaz",
    brand: "exemplu catalog",
    image: "/products/lapte-ovaz.jpg",
    categorySlug: "bauturi",
    storeSlugs: ["lidl", "carrefour", "mega-image", "kaufland"],
    score: "6.8",
    verdict: "Poate fi potrivita, dar zaharul, uleiurile si aditivii merita verificati.",
    intro:
      "Bauturile vegetale par asemanatoare, insa pot diferi mult la zahar, uleiuri, sare si adaosuri.",
    nutrients: ["zahar per 100ml", "uleiuri", "sare", "fortifiere"],
    goodFor: ["cafea", "mic dejun", "alternative vegetale"],
    watchOut: ["zahar adaugat", "uleiuri", "lista lunga de aditivi"],
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
    verdict: "Alternativa buna cand proteina este reala si zaharul ramane controlat.",
    intro:
      "Batoanele proteice sunt utile pentru comparatii SEO, fiindca multe produse promit mult, dar difera la zahar si ingrediente.",
    nutrients: ["proteina", "zahar", "fibre", "calorii"],
    goodFor: ["gustare rapida", "dupa sport", "alternative la dulciuri"],
    watchOut: ["zahar alcool", "calorii ascunse", "pret per baton"],
    alternativeSlugs: ["baton-ovaz", "skyr-simplu", "iaurt-proteic-lidl"],
  },
  {
    slug: "baton-ovaz",
    name: "Baton de ovaz dulce",
    brand: "exemplu catalog",
    image: "/products/baton-ovaz.jpg",
    categorySlug: "dulciuri",
    storeSlugs: ["carrefour", "mega-image", "profi"],
    score: "3.4",
    verdict: "Gustare dulce de verificat atent, mai ales pentru zahar si portie.",
    intro:
      "Un baton de ovaz poate parea o gustare sanatoasa, dar unele variante au mult zahar pentru o portie mica.",
    nutrients: ["zahar ridicat", "calorii", "fibre", "ingrediente"],
    goodFor: ["ocazional", "energie rapida"],
    watchOut: ["zahar pe portie", "glazuri", "portii mici dar calorice"],
    alternativeSlugs: ["baton-proteic", "skyr-simplu", "iaurt-grecesc-2"],
  },
];

export const SEO_ALTERNATIVE_GUIDES = [
  {
    slug: "iaurturi",
    title: "Alternative la iaurturi dulci",
    image: "/products/skyr.webp",
    intro:
      "Cand un iaurt pare sanatos, verifica zaharul, proteina si ingredientele. Alternativele bune sunt adesea iaurtul simplu, skyr-ul sau iaurtul grecesc.",
    categorySlugs: ["lactate"],
    productSlugs: ["baton-ovaz", "iaurt-grecesc-2", "skyr-simplu", "iaurt-simplu"],
    checks: ["zahar per 100g", "proteina", "ingrediente scurte", "fara topping dulce"],
    searchIntent: "pentru oameni care cauta iaurturi mai bune, mai simple sau mai proteice",
  },
  {
    slug: "dulciuri",
    title: "Alternative la dulciuri foarte zaharoase",
    image: "/products/baton-ovaz.jpg",
    intro:
      "Nu toate gustarile dulci sunt la fel. Unele pot fi inlocuite cu variante mai satioase sau cu zahar mai controlat.",
    categorySlugs: ["dulciuri", "snacks"],
    productSlugs: ["baton-ovaz", "baton-proteic", "skyr-simplu"],
    checks: ["zahar", "calorii per portie", "fibre", "proteina"],
    searchIntent: "pentru cautari despre dulciuri mai ok si gustari alternative",
  },
  {
    slug: "bauturi",
    title: "Alternative la bauturi cu zahar",
    image: "/products/lapte-ovaz.jpg",
    intro:
      "Bauturile pot adauga zahar fara sa para o masa. Compara valorile per 100ml si verifica indulcitorii sau ingredientele.",
    categorySlugs: ["bauturi", "produse-bio"],
    productSlugs: ["bautura-ovaz", "iaurt-simplu", "skyr-simplu"],
    checks: ["zahar per 100ml", "indulcitori", "cofeina", "ingrediente"],
    searchIntent: "pentru oameni care vor bauturi mai simple sau mai usor de comparat",
  },
  {
    slug: "snacks",
    title: "Alternative la snacks-uri sarate sau dulci",
    image: "/products/baton-proteic.jpg",
    intro:
      "La snacks conteaza mult portia, sarea, zaharul si cat de satios este produsul. Scanarea te ajuta sa compari variante similare.",
    categorySlugs: ["snacks", "dulciuri"],
    productSlugs: ["baton-proteic", "baton-ovaz", "iaurt-grecesc-2"],
    checks: ["sare", "zahar", "proteina", "calorii"],
    searchIntent: "pentru cautari despre gustari mai bune si alternative la raft",
  },
  {
    slug: "mezeluri",
    title: "Alternative la mezeluri foarte procesate",
    image: "/stores/market-local.png",
    intro:
      "Mezelurile sunt o categorie unde catalogul are nevoie de contributii reale: procent de carne, sare, aditivi si ingrediente.",
    categorySlugs: ["mezeluri"],
    productSlugs: ["iaurt-grecesc-2", "skyr-simplu"],
    checks: ["procent carne", "sare", "aditivi", "grasimi"],
    searchIntent: "pentru cautari despre mezeluri mai simple si produse mai putin procesate",
  },
  {
    slug: "cereale-mic-dejun",
    title: "Alternative la cereale de mic dejun cu mult zahar",
    image: "/products/iaurt-simplu.jpg",
    intro:
      "Cerealele pot parea potrivite pentru mic dejun, dar zaharul si fibrele schimba mult verdictul.",
    categorySlugs: ["cereale", "lactate"],
    productSlugs: ["iaurt-simplu", "skyr-simplu", "iaurt-grecesc-2"],
    checks: ["zahar", "fibre", "proteina", "ingrediente"],
    searchIntent: "pentru cautari despre mic dejun mai simplu si produse pentru familie",
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

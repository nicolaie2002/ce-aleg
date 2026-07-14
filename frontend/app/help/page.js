"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  Barcode,
  BookOpen,
  CreditCard,
  Gift,
  Languages,
  LifeBuoy,
  Mail,
  Search,
  ShieldCheck,
  Store,
  Trash2,
  UserPlus,
} from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { useLocale } from "../components/LocaleProvider";

const HELP_SECTIONS = [
  {
    id: "account",
    icon: UserPlus,
    titleRo: "Cont si autentificare",
    titleEn: "Account and sign-in",
    introRo: "Tot ce tine de creare cont, confirmare email, login si recuperarea parolei.",
    introEn: "Everything about creating an account, email confirmation, sign-in and password recovery.",
    items: [
      {
        qRo: "Cum imi fac cont?",
        qEn: "How do I create an account?",
        aRo: "Intra pe Inregistrare, completeaza numele, emailul si parola, accepta termenii, apoi confirma emailul primit. Dupa confirmare intri automat in aplicatie.",
        aEn: "Open Register, enter your name, email and password, accept the terms, then confirm the email you receive. After confirmation you enter the app automatically.",
      },
      {
        qRo: "Nu pot intra in cont.",
        qEn: "I cannot sign in.",
        aRo: "Verifica emailul si parola. Daca mesajul spune ca emailul nu este confirmat, apasa Retrimite emailul. Daca ai uitat parola, foloseste pagina Ai uitat parola.",
        aEn: "Check your email and password. If the message says the email is not confirmed, use Resend email. If you forgot the password, use Forgot password.",
      },
      {
        qRo: "Nu am primit emailul de confirmare.",
        qEn: "I did not receive the confirmation email.",
        aRo: "Verifica Spam/Promotions, asteapta 1-2 minute si apasa Retrimite emailul din pagina de login. Daca tot nu vine, scrie-ne din Suport cu emailul contului.",
        aEn: "Check Spam/Promotions, wait 1-2 minutes and press Resend email from the login page. If it still does not arrive, contact Support with your account email.",
      },
    ],
  },
  {
    id: "scan",
    icon: Barcode,
    titleRo: "Scanare produse",
    titleEn: "Product scanning",
    introRo: "Cum scanezi coduri de bare, ce faci cand codul e gresit si cum trimiti produse lipsa.",
    introEn: "How to scan barcodes, what to do when the code is wrong and how to submit missing products.",
    items: [
      {
        qRo: "Cum scanez un produs?",
        qEn: "How do I scan a product?",
        aRo: "Deschide Scanare, permite camera, incadreaza codul de bare si confirma codul citit. Daca produsul exista, vezi verdictul si alternativele.",
        aEn: "Open Scanner, allow camera access, frame the barcode and confirm the detected code. If the product exists, you see the verdict and alternatives.",
      },
      {
        qRo: "Scannerul a citit codul gresit.",
        qEn: "The scanner read the wrong code.",
        aRo: "La inceputul flow-ului confirma codul. Daca nu este corect, alege rescaneaza sau corecteaza manual inainte sa cauti produsul.",
        aEn: "At the start of the flow, confirm the code. If it is not correct, choose scan again or fix it manually before searching.",
      },
      {
        qRo: "Produsul nu este gasit.",
        qEn: "The product is not found.",
        aRo: "Alege Adauga produs. Codul ramane completat, faci poza la fata produsului si la tabelul nutritional, OCR-ul completeaza ce poate, apoi trimiti la verificare.",
        aEn: "Choose Add product. The barcode stays filled in, you take a front photo and a nutrition-label photo, OCR fills what it can, then you submit for review.",
      },
      {
        qRo: "Camera nu porneste.",
        qEn: "The camera does not start.",
        aRo: "Verifica permisiunea camerei in browser, foloseste HTTPS, inchide alte aplicatii care folosesc camera si reincarca pagina.",
        aEn: "Check camera permission in the browser, use HTTPS, close other apps using the camera and reload the page.",
      },
    ],
  },
  {
    id: "store-mode",
    icon: Store,
    titleRo: "Modul La magazin",
    titleEn: "In-store mode",
    introRo: "Alege magazinul inainte de scanare pentru recomandari si misiuni mai relevante.",
    introEn: "Pick the store before scanning for more relevant recommendations and missions.",
    items: [
      {
        qRo: "De ce aleg magazinul?",
        qEn: "Why should I pick a store?",
        aRo: "Scanarile se salveaza cu magazinul ales, alternativele pot fi prioritizate pentru acel magazin, iar misiunile pot deveni mai utile.",
        aEn: "Scans are saved with the selected store, alternatives can be prioritized for that store, and missions become more useful.",
      },
      {
        qRo: "Pot schimba magazinul?",
        qEn: "Can I change the store?",
        aRo: "Da. Intra in pagina Magazin si alege alt magazin inainte de urmatoarea scanare.",
        aEn: "Yes. Open Store and choose another store before your next scan.",
      },
    ],
  },
  {
    id: "missions",
    icon: Gift,
    titleRo: "Misiuni si CeCoins",
    titleEn: "Missions and CeCoins",
    introRo: "CeCoins se castiga prin misiuni, produse aprobate si actiuni utile pentru catalog.",
    introEn: "CeCoins are earned through missions, approved products and useful catalog actions.",
    items: [
      {
        qRo: "Cum primesc CeCoins?",
        qEn: "How do I receive CeCoins?",
        aRo: "Finalizeaza misiuni, adauga produse care sunt aprobate sau participa la actiuni speciale. Unele recompense apar dupa verificarea adminului.",
        aEn: "Complete missions, add products that get approved or join special actions. Some rewards appear after admin review.",
      },
      {
        qRo: "De ce nu am primit recompensa imediat?",
        qEn: "Why did I not receive the reward immediately?",
        aRo: "Produsele noi trebuie verificate ca sa evitam duplicate, poze neclare sau date gresite. Dupa aprobare primesti recompensa.",
        aEn: "New products must be reviewed to avoid duplicates, unclear photos or wrong data. After approval you receive the reward.",
      },
    ],
  },
  {
    id: "billing",
    icon: CreditCard,
    titleRo: "Planuri, plati si CeCoins cumparati",
    titleEn: "Plans, payments and purchased CeCoins",
    introRo: "Pentru cumpararea planurilor sau CeCoins ai nevoie de cont si sesiune activa.",
    introEn: "To buy plans or CeCoins you need an account and an active session.",
    items: [
      {
        qRo: "Pot cumpara fara cont?",
        qEn: "Can I buy without an account?",
        aRo: "Nu. Planurile si CeCoins trebuie legate de un cont, altfel aplicatia nu are unde sa activeze beneficiile.",
        aEn: "No. Plans and CeCoins must be attached to an account, otherwise the app has nowhere to activate the benefits.",
      },
      {
        qRo: "Plata a mers, dar planul nu apare.",
        qEn: "Payment worked, but the plan does not show.",
        aRo: "Reincarca pagina Pricing sau Dashboard. Daca nu apare dupa cateva minute, contacteaza Suport cu emailul contului si detaliile platii.",
        aEn: "Reload Pricing or Dashboard. If it does not appear after a few minutes, contact Support with your account email and payment details.",
      },
      {
        qRo: "Cum administrez abonamentul?",
        qEn: "How do I manage my subscription?",
        aRo: "Din Pricing apare butonul Administreaza abonamentul daca ai abonament Stripe activ.",
        aEn: "Pricing shows the Manage subscription button when you have an active Stripe subscription.",
      },
    ],
  },
  {
    id: "preferences",
    icon: ShieldCheck,
    titleRo: "Preferinte, familie si recomandari",
    titleEn: "Preferences, family and recommendations",
    introRo: "Setarile ajuta aplicatia sa aleaga alternative mai potrivite pentru tine.",
    introEn: "Settings help the app choose alternatives that fit you better.",
    items: [
      {
        qRo: "Cum schimb preferintele?",
        qEn: "How do I change preferences?",
        aRo: "Intra in Preferinte si seteaza ce conteaza pentru tine: zahar, proteina, ingrediente, alergeni sau obiective.",
        aEn: "Open Preferences and set what matters to you: sugar, protein, ingredients, allergens or goals.",
      },
      {
        qRo: "Cum functioneaza profilurile Family?",
        qEn: "How do Family profiles work?",
        aRo: "Planul Family poate folosi profiluri separate, cu preferinte si cosuri diferite pentru membrii casei.",
        aEn: "The Family plan can use separate profiles, with different preferences and carts for household members.",
      },
    ],
  },
  {
    id: "language",
    icon: Languages,
    titleRo: "Limba si afisare",
    titleEn: "Language and display",
    introRo: "Poti schimba limba si tema din butoanele din header.",
    introEn: "You can change language and theme from the header buttons.",
    items: [
      {
        qRo: "Cum schimb limba?",
        qEn: "How do I change the language?",
        aRo: "Apasa butonul RO/EN din partea de sus. Alegerea ramane salvata in browser.",
        aEn: "Press the RO/EN button at the top. Your choice stays saved in the browser.",
      },
      {
        qRo: "Ce fac daca vad texte in limba gresita?",
        qEn: "What if I see text in the wrong language?",
        aRo: "Reincarca pagina. Daca problema ramane, trimite pagina si o captura prin Suport.",
        aEn: "Reload the page. If the issue remains, send the page and a screenshot through Support.",
      },
    ],
  },
  {
    id: "privacy",
    icon: Trash2,
    titleRo: "Date personale si stergere cont",
    titleEn: "Personal data and account deletion",
    introRo: "Ai control asupra contului si poti cere stergerea datelor.",
    introEn: "You control your account and can request data deletion.",
    items: [
      {
        qRo: "Cum imi sterg contul?",
        qEn: "How do I delete my account?",
        aRo: "Intra in Stergere cont, cere linkul de confirmare si finalizeaza stergerea din email. Actiunea este definitiva.",
        aEn: "Open Delete account, request the confirmation link and finish deletion from email. This action is permanent.",
      },
      {
        qRo: "Ce date sunt folosite?",
        qEn: "What data is used?",
        aRo: "Folosim date de cont, preferinte, istoric de scanare, cos si contributii ca sa oferim recomandari si functionalitati. Detaliile sunt in Politica de confidentialitate.",
        aEn: "We use account data, preferences, scan history, cart and contributions to provide recommendations and features. Details are in the Privacy Policy.",
      },
    ],
  },
  {
    id: "contact",
    icon: LifeBuoy,
    titleRo: "Contact si probleme",
    titleEn: "Contact and issues",
    introRo: "Daca ceva nu merge, trimite-ne cat mai multe detalii ca sa putem reproduce problema.",
    introEn: "If something does not work, send enough details so we can reproduce it.",
    items: [
      {
        qRo: "Ce trimit la suport?",
        qEn: "What should I send to support?",
        aRo: "Trimite emailul contului, pagina unde apare problema, ce ai apasat, mesajul de eroare si o captura daca se poate.",
        aEn: "Send your account email, the page where the issue appears, what you clicked, the error message and a screenshot if possible.",
      },
      {
        qRo: "Unde trimit problema?",
        qEn: "Where do I send the issue?",
        aRo: "Foloseste pagina Suport sau scrie la contact@cealeg.shop.",
        aEn: "Use the Support page or write to contact@cealeg.shop.",
      },
    ],
  },
];

function matchesQuery(section, query) {
  if (!query) return true;

  const haystack = [
    section.titleRo,
    section.titleEn,
    section.introRo,
    section.introEn,
    ...section.items.flatMap((item) => [item.qRo, item.qEn, item.aRo, item.aEn]),
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(query.toLowerCase());
}

export default function HelpPage() {
  const { pick } = useLocale();
  const [query, setQuery] = useState("");
  const visibleSections = useMemo(
    () => HELP_SECTIONS.filter((section) => matchesQuery(section, query.trim())),
    [query]
  );

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/support" actionLabel={pick("Contact", "Contact")} />

      <section className="ce-shell ce-page pb-28">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.85fr)_minmax(18rem,0.45fr)] lg:items-end">
          <div>
            <p className="inline-flex items-center gap-2 rounded-lg border border-cyan-300/25 bg-cyan-300/10 px-3 py-2 text-xs font-black uppercase tracking-[0.14em] text-cyan-100">
              <BookOpen size={15} />
              {pick("Centru de ajutor", "Help Center")}
            </p>
            <h1 className="mt-5 max-w-4xl text-4xl font-black leading-tight md:text-6xl">
              {pick("Cum folosesti Ce aleg?", "How to use Ce aleg?")}
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-gray-300 md:text-lg">
              {pick(
                "Gaseste rapid raspunsuri despre cont, scanare, produse lipsa, misiuni, plati si probleme frecvente.",
                "Quickly find answers about accounts, scanning, missing products, missions, payments and common issues."
              )}
            </p>
          </div>

          <div className="rounded-lg border border-white/10 bg-[#101820]/88 p-4 shadow-2xl shadow-black/20">
            <label className="text-sm font-black text-gray-200" htmlFor="help-search">
              {pick("Cauta in ajutor", "Search help")}
            </label>
            <div className="mt-3 flex items-center gap-3 rounded-lg border border-white/10 bg-black/30 px-3">
              <Search size={18} className="text-cyan-200" />
              <input
                id="help-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={pick("Ex: camera, parola, CeCoins", "Example: camera, password, CeCoins")}
                className="min-h-12 w-full bg-transparent text-sm font-semibold text-white outline-none placeholder:text-gray-500"
              />
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
          <aside className="h-fit rounded-lg border border-white/10 bg-[#101820]/82 p-4 lg:sticky lg:top-24">
            <p className="mb-3 text-xs font-black uppercase tracking-[0.14em] text-gray-400">
              {pick("Cuprins", "Contents")}
            </p>
            <nav className="grid gap-1">
              {visibleSections.map((section) => (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-bold text-gray-300 hover:bg-white/[0.07] hover:text-white"
                >
                  <section.icon size={16} className="text-cyan-200" />
                  {pick(section.titleRo, section.titleEn)}
                </a>
              ))}
            </nav>
          </aside>

          <div className="space-y-5">
            {visibleSections.length ? (
              visibleSections.map((section) => {
                const Icon = section.icon;

                return (
                  <section
                    key={section.id}
                    id={section.id}
                    className="scroll-mt-24 rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15"
                  >
                    <div className="mb-5 flex items-start gap-3">
                      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-cyan-300/25 bg-cyan-300/10 text-cyan-100">
                        <Icon size={21} />
                      </span>
                      <div>
                        <h2 className="text-2xl font-black text-white">
                          {pick(section.titleRo, section.titleEn)}
                        </h2>
                        <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-400">
                          {pick(section.introRo, section.introEn)}
                        </p>
                      </div>
                    </div>

                    <div className="grid gap-3">
                      {section.items.map((item) => (
                        <article key={item.qRo} className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
                          <h3 className="text-base font-black text-white">
                            {pick(item.qRo, item.qEn)}
                          </h3>
                          <p className="mt-2 text-sm leading-6 text-gray-300">
                            {pick(item.aRo, item.aEn)}
                          </p>
                        </article>
                      ))}
                    </div>
                  </section>
                );
              })
            ) : (
              <div className="rounded-lg border border-white/10 bg-white/[0.04] p-6 text-gray-300">
                <p className="font-black text-white">{pick("Niciun rezultat", "No results")}</p>
                <p className="mt-2 text-sm">
                  {pick(
                    "Incearca alt cuvant sau trimite problema prin Suport.",
                    "Try another word or send the issue through Support."
                  )}
                </p>
              </div>
            )}

            <section className="grid gap-4 rounded-lg border border-emerald-300/20 bg-emerald-300/10 p-5 sm:grid-cols-[1fr_auto] sm:items-center">
              <div>
                <p className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.14em] text-emerald-100">
                  <Mail size={17} />
                  {pick("Ai ramas blocat?", "Still stuck?")}
                </p>
                <h2 className="mt-2 text-2xl font-black text-white">
                  {pick("Trimite-ne problema si o verificam.", "Send us the issue and we will check it.")}
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-300">
                  {pick(
                    "Include pagina, contul, pasii facuti si mesajul de eroare. Asa putem repara mai repede.",
                    "Include the page, account, steps taken and error message. That helps us fix it faster."
                  )}
                </p>
              </div>
              <Link
                href="/support"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
              >
                <LifeBuoy size={18} />
                {pick("Contact suport", "Contact support")}
              </Link>
            </section>
          </div>
        </div>
      </section>
    </main>
  );
}

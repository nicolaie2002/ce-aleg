"use client";

import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  Camera,
  Cookie,
  Crown,
  Database,
  FileCheck2,
  Globe2,
  LockKeyhole,
  Mail,
  Scale,
  Server,
  ShieldCheck,
  Trash2,
  UserCheck,
} from "lucide-react";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";

const CONTACT_EMAIL = "contact@cealeg.shop";
const LAST_UPDATED_RO = "22 iunie 2026";
const LAST_UPDATED_EN = "June 22, 2026";

function InfoCard({ icon: Icon, title, children }) {
  return (
    <section className="ce-panel-interactive rounded-xl border border-white/10 bg-black/25 p-5">
      <Icon className="text-cyan-200" size={21} />
      <h2 className="mt-3 text-lg font-black">{title}</h2>
      <div className="mt-2 space-y-2 leading-7 text-gray-300">{children}</div>
    </section>
  );
}

function BulletList({ items }) {
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-300" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function PrivacyPage() {
  const { pick } = useLocale();

  const collectedData = [
    pick(
      "date de cont: nume afișat, email, parolă hash-uită, status de verificare email, sesiuni și preferințe de limbă/temă",
      "account data: display name, email, hashed password, email verification status, sessions and language/theme preferences"
    ),
    pick(
      "date de folosire: coduri de bare căutate, scanări, rezultate, istoric, coș, favorite, preferințe alimentare și profiluri Family",
      "usage data: searched barcodes, scans, results, history, cart, favorites, food preferences and Family profiles"
    ),
    pick(
      "date trimise de tine: produse contribuite, fotografii de produs, prețuri, magazine, descrieri și corecturi",
      "data submitted by you: contributed products, product photos, prices, stores, descriptions and corrections"
    ),
    pick(
      "date tehnice: adresă IP, browser, dispozitiv, loguri de securitate, erori, rate limiting și evenimente antifraudă",
      "technical data: IP address, browser, device, security logs, errors, rate limiting and anti-fraud events"
    ),
    pick(
      "date de abonament: plan, status plată, ID client Stripe și ID abonament; nu stocăm numărul cardului",
      "subscription data: plan, payment status, Stripe customer ID and subscription ID; we do not store card numbers"
    ),
  ];

  const purposes = [
    pick("crearea contului, autentificare, verificare email și resetare parolă", "account creation, sign-in, email verification and password reset"),
    pick("scanarea produselor, afișarea verdictului, alternativelor, coșului, favoritelor și istoricului", "product scanning, verdicts, alternatives, cart, favorites and history"),
    pick("administrarea abonamentelor, facturării, limitelor Free/Pro/Family și suportului", "subscription, billing, Free/Pro/Family limits and support administration"),
    pick("securitate: prevenirea abuzului, atacurilor, conturilor false și cererilor automate", "security: preventing abuse, attacks, fake accounts and automated requests"),
    pick("îmbunătățirea produsului prin statistici agregate și Analytics doar dacă accepți cookie-urile opționale", "improving the product through aggregated statistics and Analytics only if you accept optional cookies"),
  ];

  const processors = [
    "Supabase - bază de date și stocare pentru produse/imagini",
    "Render - găzduire backend/API",
    "Vercel - găzduire frontend",
    "Stripe - plăți, abonamente, facturi și portal client",
    "Brevo - emailuri tranzacționale",
    "Google Analytics - statistici doar după consimțământ",
    "Open Food Facts - identificare și completare date produs din catalog public",
  ];

  const rights = [
    pick("acces la datele tale", "access your data"),
    pick("corectarea datelor incorecte", "correct inaccurate data"),
    pick("ștergerea datelor când condițiile legale sunt îndeplinite", "erase data when legal conditions are met"),
    pick("restricționarea sau opoziția la anumite prelucrări", "restrict or object to certain processing"),
    pick("portabilitatea datelor, când se aplică", "data portability, where applicable"),
    pick("retragerea consimțământului pentru Analytics/cookie-uri opționale", "withdraw consent for Analytics/optional cookies"),
    pick("plângere la Autoritatea Națională de Supraveghere a Prelucrării Datelor cu Caracter Personal", "lodge a complaint with the Romanian data protection authority"),
  ];

  return (
    <main className="min-h-screen text-white">
      <section className="ce-shell-md ce-page">
        <div className="flex items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> {pick("Pagina principală", "Home")}
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href="/pricing"
              className="inline-flex items-center gap-1 rounded-lg border border-yellow-300/35 px-3 py-2 text-sm font-black text-yellow-200 hover:bg-yellow-300/10"
            >
              <Crown size={15} /> {pick("Planuri", "Plans")}
            </Link>
            <LanguageSwitcher compact />
            <ThemeSwitcher />
          </div>
        </div>

        <div className="mt-10 rounded-2xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur md:p-8">
          <p className="flex items-center gap-2 text-sm font-bold text-cyan-200">
            <ShieldCheck size={17} /> {pick("Politica de confidențialitate", "Privacy policy")}
          </p>
          <h1 className="mt-3 text-4xl font-black md:text-5xl">
            {pick("Cum protejăm datele tale.", "How we protect your data.")}
          </h1>
          <p className="mt-4 max-w-3xl leading-8 text-gray-300">
            {pick(
              `Această politică explică ce date prelucrăm în Ce aleg?, de ce avem nevoie de ele și ce drepturi ai. Ultima actualizare: ${LAST_UPDATED_RO}.`,
              `This policy explains what data Ce aleg? processes, why we need it and what rights you have. Last updated: ${LAST_UPDATED_EN}.`
            )}
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <InfoCard icon={UserCheck} title={pick("Operator și contact", "Controller and contact")}>
              <p>
                {pick(
                  "Operatorul serviciului Ce aleg? poate fi contactat pentru orice întrebare despre datele personale la",
                  "The controller of the Ce aleg? service can be contacted for any personal data question at"
                )}{" "}
                <a href={`mailto:${CONTACT_EMAIL}`} className="font-bold text-cyan-200 hover:text-white">
                  {CONTACT_EMAIL}
                </a>
                .
              </p>
              <p>
                {pick(
                  "Site-ul oficial este https://www.cealeg.shop.",
                  "The official website is https://www.cealeg.shop."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={Scale} title={pick("Cine poate folosi aplicația", "Who can use the app")}>
              <p>
                {pick(
                  "Conturile sunt pentru persoane de cel puțin 16 ani sau pentru minori care folosesc aplicația cu acordul și supravegherea părintelui/tutorelui. Nu cerem în mod intenționat date de la copii sub 13 ani.",
                  "Accounts are for people who are at least 16 years old, or for minors using the app with parent/guardian consent and supervision. We do not knowingly request data from children under 13."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={Database} title={pick("Date pe care le colectăm", "Data we collect")}>
              <BulletList items={collectedData} />
            </InfoCard>

            <InfoCard icon={FileCheck2} title={pick("De ce le folosim", "Why we use it")}>
              <BulletList items={purposes} />
            </InfoCard>

            <InfoCard icon={LockKeyhole} title={pick("Temeiuri legale", "Legal bases")}>
              <p>
                {pick(
                  "Prelucrăm datele pentru executarea serviciului cerut de tine, pentru obligații legale, pentru interes legitim de securitate și funcționare, iar pentru Analytics/cookie-uri opționale doar pe baza consimțământului tău.",
                  "We process data to provide the service you request, comply with legal obligations, protect security and operations through legitimate interest, and for Analytics/optional cookies only with your consent."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={Camera} title={pick("Cameră, microfon și scanări", "Camera, microphone and scans")}>
              <p>
                {pick(
                  "Camera și microfonul pornesc doar după permisiunea ta în browser. Cadrele, codurile de bare și textul citit de pe etichetă sunt folosite pentru identificarea produsului și afișarea rezultatului.",
                  "The camera and microphone start only after browser permission. Frames, barcodes and label text are used to identify the product and show the result."
                )}
              </p>
              <p>
                {pick(
                  "Asistentul AI vizual este în dezvoltare; momentan serviciul se bazează pe coduri de bare, OCR local și surse de catalog.",
                  "The visual AI assistant is in development; for now the service relies on barcodes, local OCR and catalog sources."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={Server} title={pick("Furnizori și procesatori", "Providers and processors")}>
              <BulletList items={processors} />
              <p>
                {pick(
                  "Folosim acești furnizori doar pentru funcționarea serviciului, plăți, emailuri, găzduire, securitate și analiză cu consimțământ.",
                  "We use these providers only for service operation, payments, emails, hosting, security and consent-based analytics."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={Globe2} title={pick("Transferuri internaționale", "International transfers")}>
              <p>
                {pick(
                  "Unii furnizori pot procesa date în afara Spațiului Economic European. În aceste cazuri ne bazăm pe garanțiile oferite de furnizori, cum ar fi clauze contractuale standard sau mecanisme echivalente prevăzute de GDPR.",
                  "Some providers may process data outside the European Economic Area. In those cases we rely on provider safeguards such as Standard Contractual Clauses or equivalent GDPR mechanisms."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={Cookie} title={pick("Cookie-uri și stocare locală", "Cookies and local storage")}>
              <p>
                {pick(
                  "Folosim cookie-uri și localStorage necesare pentru sesiune, securitate, limbă, temă și preferințe. Google Analytics se încarcă doar dacă accepți cookie-urile opționale din banner.",
                  "We use cookies and localStorage needed for session, security, language, theme and preferences. Google Analytics loads only if you accept optional cookies in the banner."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={BarChart3} title={pick("Analytics", "Analytics")}>
              <p>
                {pick(
                  "Dacă accepți Analytics, putem vedea statistici agregate despre pagini vizitate, dispozitive și performanță. Poți refuza sau retrage consimțământul ștergând preferința de cookie din browser.",
                  "If you accept Analytics, we may see aggregated statistics about visited pages, devices and performance. You can refuse or withdraw consent by clearing the cookie preference in your browser."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={Trash2} title={pick("Păstrare și ștergere", "Retention and deletion")}>
              <p>
                {pick(
                  "Datele de cont, coș, favorite, istoric și preferințe se păstrează cât timp ai contul activ. Datele de facturare se păstrează cât cere legea. Logurile de securitate se păstrează pe perioade limitate rezonabile.",
                  "Account, cart, favorites, history and preference data is kept while your account is active. Billing data is kept as required by law. Security logs are kept for reasonable limited periods."
                )}
              </p>
              <p>
                {pick(
                  "Poți cere ștergerea contului din dashboard; confirmarea se face prin email. Unele date pot fi păstrate sau anonimizate dacă sunt necesare legal, pentru securitate sau pentru apărarea unor drepturi.",
                  "You can request account deletion from the dashboard; confirmation is made by email. Some data may be retained or anonymized if required by law, security or legal claims."
                )}
              </p>
            </InfoCard>

            <InfoCard icon={Mail} title={pick("Emailuri", "Emails")}>
              <p>
                {pick(
                  "Trimitem emailuri pentru verificarea contului, bun venit, resetare parolă, confirmare ștergere, abonamente și securitate. Emailurile de marketing vor fi separate și opționale.",
                  "We send emails for account verification, welcome, password reset, deletion confirmation, subscriptions and security. Marketing emails will be separate and optional."
                )}
              </p>
            </InfoCard>
          </div>

          <section className="mt-8 rounded-xl border border-cyan-300/25 bg-cyan-300/10 p-5">
            <h2 className="flex items-center gap-2 text-xl font-black text-cyan-100">
              <UserCheck size={20} /> {pick("Drepturile tale", "Your rights")}
            </h2>
            <p className="mt-3 max-w-4xl leading-7 text-gray-300">
              {pick(
                "Conform GDPR, poți cere următoarele. Pentru a-ți proteja contul, este posibil să îți cerem să confirmi identitatea înainte de a răspunde.",
                "Under the GDPR, you can request the following. To protect your account, we may ask you to confirm your identity before responding."
              )}
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <BulletList items={rights} />
              <div className="rounded-lg border border-white/10 bg-black/25 p-4 leading-7 text-gray-300">
                {pick(
                  "Îți răspundem de regulă în cel mult o lună. Dacă ești nemulțumit de răspuns, poți depune plângere la ANSPDCP.",
                  "We usually respond within one month. If you are unhappy with the response, you may complain to the Romanian data protection authority."
                )}
              </div>
            </div>
          </section>

          <section className="mt-5 rounded-xl border border-yellow-300/25 bg-yellow-300/10 p-5 text-yellow-100">
            <h2 className="font-black">{pick("Notă importantă", "Important note")}</h2>
            <p className="mt-2 leading-7">
              {pick(
                "Ce aleg? oferă informații orientative despre produse alimentare. Verifică mereu eticheta, alergenii, prețul real și recomandările unui specialist dacă ai restricții medicale sau alimentare.",
                "Ce aleg? provides informational guidance about food products. Always check the label, allergens, real shelf price and professional advice if you have medical or dietary restrictions."
              )}
            </p>
          </section>

          <section className="mt-5 rounded-xl border border-white/10 bg-black/25 p-5">
            <h2 className="font-black">{pick("Surse oficiale folosite", "Official references used")}</h2>
            <div className="mt-3 grid gap-2 text-sm font-semibold text-cyan-100 md:grid-cols-2">
              <a className="hover:text-white" href="https://commission.europa.eu/law/law-topic/data-protection/information-individuals_en" target="_blank" rel="noreferrer">
                European Commission - GDPR rights
              </a>
              <a className="hover:text-white" href="https://www.dataprotection.ro/?lang=ro&page=Transmiterea_plangerilor_catre_ANSPDCP" target="_blank" rel="noreferrer">
                ANSPDCP - drepturi și plângeri
              </a>
              <a className="hover:text-white" href="https://commission.europa.eu/cookies-policy_en" target="_blank" rel="noreferrer">
                European Commission - cookies
              </a>
              <a className="hover:text-white" href="https://commission.europa.eu/news-and-media/news/ten-years-gdpr-your-data-your-rights-2026-05-22_en" target="_blank" rel="noreferrer">
                European Commission - your data, your rights
              </a>
            </div>
          </section>

          <section className="mt-5 rounded-xl border border-white/10 bg-black/25 p-5">
            <h2 className="font-black">{pick("Contact pentru date personale", "Personal data contact")}</h2>
            <p className="mt-2 leading-7 text-gray-300">
              {pick("Scrie-ne la", "Contact us at")}{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="font-bold text-cyan-200 hover:text-white">
                {CONTACT_EMAIL}
              </a>
              {pick(" pentru acces, rectificare, ștergere, export sau întrebări despre confidențialitate.", " for access, correction, deletion, export or privacy questions.")}
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}

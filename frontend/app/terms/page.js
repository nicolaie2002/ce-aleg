"use client";

import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  Ban,
  Crown,
  FileText,
  Mail,
  Scale,
  ShieldCheck,
  ShoppingCart,
  Trash2,
  UploadCloud,
  Users,
  Wallet,
} from "lucide-react";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";

const CONTACT_EMAIL = "contact@cealeg.shop";
const LAST_UPDATED_RO = "22 iunie 2026";
const LAST_UPDATED_EN = "June 22, 2026";

function TermCard({ icon: Icon, title, children }) {
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

export default function TermsPage() {
  const { pick } = useLocale();

  const fairUse = [
    pick("nu încerca să ocolești limitele Free/Pro/Family sau verificările de securitate", "do not try to bypass Free/Pro/Family limits or security checks"),
    pick("nu ataca API-ul, nu trimite payload-uri malițioase și nu folosi automatizări abuzive", "do not attack the API, send malicious payloads or use abusive automation"),
    pick("nu copia masiv catalogul și nu folosi datele pentru spam, fraudă sau servicii concurente abuzive", "do not bulk-copy the catalog or use data for spam, fraud or abusive competing services"),
    pick("nu încărca fotografii care conțin persoane, date personale, conținut ilegal sau materiale pentru care nu ai drepturi", "do not upload photos containing people, personal data, illegal content or materials you do not have rights to"),
  ];

  const subscriptions = [
    pick("Free poate avea limite de scanări și un număr mai mic de alternative afișate.", "Free may have scan limits and fewer displayed alternatives."),
    pick("Pro și Family pot debloca scanări nelimitate, alternative suplimentare și funcții avansate.", "Pro and Family may unlock unlimited scans, extra alternatives and advanced features."),
    pick("Plățile și facturile sunt procesate prin Stripe; Ce aleg? nu stochează datele complete ale cardului.", "Payments and invoices are processed through Stripe; Ce aleg? does not store full card details."),
    pick("Poți administra sau anula abonamentul din portalul de client. Drepturile tale legale de consumator rămân aplicabile.", "You can manage or cancel your subscription from the customer portal. Your statutory consumer rights remain unaffected."),
  ];

  const thirdParties = [
    "Stripe - plăți, abonamente, facturi și portal client",
    "Brevo - emailuri tranzacționale",
    "Supabase - bază de date și stocare",
    "Render și Vercel - găzduire aplicație",
    "Open Food Facts - catalog public de produse",
    "Google Analytics - statistici doar cu acordul tău",
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
            <FileText size={17} /> {pick("Termeni și condiții", "Terms and conditions")}
          </p>
          <h1 className="mt-3 text-4xl font-black md:text-5xl">
            {pick("Reguli clare pentru folosirea Ce aleg?.", "Clear rules for using Ce aleg?.")}
          </h1>
          <p className="mt-4 max-w-3xl leading-8 text-gray-300">
            {pick(
              `Acești termeni explică ce oferă aplicația, ce responsabilități ai și care sunt limitele serviciului. Ultima actualizare: ${LAST_UPDATED_RO}.`,
              `These terms explain what the app provides, your responsibilities and service limits. Last updated: ${LAST_UPDATED_EN}.`
            )}
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <TermCard icon={Scale} title={pick("Acceptarea termenilor", "Accepting the terms")}>
              <p>
                {pick(
                  "Prin crearea unui cont, accesarea site-ului sau folosirea aplicației accepți acești termeni și Politica de confidențialitate. Dacă nu ești de acord, nu folosi serviciul.",
                  "By creating an account, accessing the website or using the app, you accept these terms and the Privacy Policy. If you do not agree, do not use the service."
                )}
              </p>
            </TermCard>

            <TermCard icon={BadgeCheck} title={pick("Ce oferă Ce aleg?", "What does Ce aleg? provide?")}>
              <p>
                {pick(
                  "Ce aleg? te ajută să scanezi produse alimentare, să vezi un verdict rapid, să compari alternative și să salvezi coș, favorite și istoric.",
                  "Ce aleg? helps you scan food products, see a quick verdict, compare alternatives and save cart, favorites and history."
                )}
              </p>
            </TermCard>

            <TermCard icon={ShieldCheck} title={pick("Vârsta minimă", "Minimum age")}>
              <p>
                {pick(
                  "Pentru cont ai nevoie de cel puțin 16 ani sau acordul părintelui/tutorelui. Serviciul nu este destinat copiilor sub 13 ani și nu cerem intenționat date de la aceștia.",
                  "To create an account, you must be at least 16 or have parent/guardian consent. The service is not intended for children under 13 and we do not knowingly request their data."
                )}
              </p>
            </TermCard>

            <TermCard icon={ShoppingCart} title={pick("Contul tău", "Your account")}>
              <p>
                {pick(
                  "Ești responsabil pentru corectitudinea datelor din cont și pentru păstrarea parolei în siguranță. Poți fi nevoit să verifici emailul pentru a folosi complet serviciul.",
                  "You are responsible for accurate account data and keeping your password safe. You may need to verify your email to fully use the service."
                )}
              </p>
            </TermCard>

            <TermCard icon={Wallet} title={pick("Abonamente și plăți", "Subscriptions and payments")}>
              <BulletList items={subscriptions} />
            </TermCard>

            <TermCard icon={Users} title={pick("Planul Family", "Family plan")}>
              <p>
                {pick(
                  "Family este gândit pentru gospodărie: profiluri separate pentru preferințe și recomandări. Proprietarul contului rămâne responsabil pentru folosirea contului și pentru persoanele adăugate.",
                  "Family is designed for a household: separate profiles for preferences and recommendations. The account owner remains responsible for account use and added members."
                )}
              </p>
            </TermCard>

            <TermCard icon={AlertTriangle} title={pick("Nu este sfat medical", "Not medical advice")}>
              <p>
                {pick(
                  "Scorurile, verdicturile și alternativele sunt informative. Nu înlocuiesc sfatul medicului, nutriționistului, eticheta oficială, informațiile despre alergeni sau prețul afișat în magazin.",
                  "Scores, verdicts and alternatives are informational. They do not replace advice from a doctor, nutritionist, the official label, allergen information or the shelf price."
                )}
              </p>
            </TermCard>

            <TermCard icon={AlertTriangle} title={pick("Limitări ale catalogului", "Catalog limitations")}>
              <p>
                {pick(
                  "Produsele pot veni din Open Food Facts, catalogul nostru, contribuții ale utilizatorilor sau magazine. Datele pot fi incomplete, greșite, traduse imperfect, neactualizate sau indisponibile pentru anumite produse.",
                  "Products may come from Open Food Facts, our catalog, user contributions or stores. Data may be incomplete, wrong, imperfectly translated, outdated or unavailable for some products."
                )}
              </p>
            </TermCard>

            <TermCard icon={UploadCloud} title={pick("Produse contribuite", "Contributed products")}>
              <p>
                {pick(
                  "Dacă încarci produse, imagini, prețuri sau descrieri, confirmi că ai dreptul să le trimiți și că informațiile sunt corecte după cunoștința ta. Ne dai dreptul să le folosim, afișăm, corectăm, moderăm sau ștergem în cadrul serviciului.",
                  "If you upload products, images, prices or descriptions, you confirm you have the right to submit them and that the information is accurate to your knowledge. You allow us to use, display, correct, moderate or delete them within the service."
                )}
              </p>
            </TermCard>

            <TermCard icon={Ban} title={pick("Utilizare interzisă", "Prohibited use")}>
              <BulletList items={fairUse} />
            </TermCard>

            <TermCard icon={Trash2} title={pick("Ștergerea sau suspendarea contului", "Account deletion or suspension")}>
              <p>
                {pick(
                  "Poți cere ștergerea contului din dashboard. Pentru protecția ta, ștergerea se confirmă prin email. Putem suspenda sau închide conturi care abuzează serviciul, încalcă legea sau atacă sistemele.",
                  "You can request account deletion from the dashboard. For your protection, deletion is confirmed by email. We may suspend or close accounts that abuse the service, break the law or attack systems."
                )}
              </p>
            </TermCard>

            <TermCard icon={FileText} title={pick("Servicii terțe", "Third-party services")}>
              <BulletList items={thirdParties} />
              <p>
                {pick(
                  "Aceste servicii pot avea propriii termeni și politici. Le folosim pentru ca aplicația să poată funcționa, încasa plăți, trimite emailuri și afișa date de produs.",
                  "These services may have their own terms and policies. We use them so the app can operate, collect payments, send emails and display product data."
                )}
              </p>
            </TermCard>
          </div>

          <section className="mt-8 rounded-xl border border-red-300/25 bg-red-300/10 p-5 text-red-100">
            <h2 className="font-black">{pick("Limitarea răspunderii", "Limitation of liability")}</h2>
            <p className="mt-2 leading-7">
              {pick(
                "Folosirea aplicației este pe propria ta decizie. Facem eforturi să afișăm informații utile și corecte, dar nu garantăm că fiecare scanare, preț, ingredient, scor sau recomandare este completă sau fără eroare.",
                "You use the app at your own discretion. We work to show useful and accurate information, but we do not guarantee that every scan, price, ingredient, score or recommendation is complete or error-free."
              )}
            </p>
          </section>

          <section className="mt-5 rounded-xl border border-cyan-300/25 bg-cyan-300/10 p-5">
            <h2 className="font-black text-cyan-100">{pick("Schimbări ale termenilor", "Changes to the terms")}</h2>
            <p className="mt-2 leading-7 text-gray-300">
              {pick(
                "Putem actualiza termenii când schimbăm funcționalități, furnizori, planuri sau cerințe legale. Pentru schimbări importante, vom încerca să anunțăm utilizatorii prin site sau email.",
                "We may update the terms when we change features, providers, plans or legal requirements. For important changes, we will try to notify users through the site or email."
              )}
            </p>
          </section>

          <section className="mt-5 rounded-xl border border-white/10 bg-black/25 p-5">
            <h2 className="flex items-center gap-2 font-black">
              <Mail size={18} /> {pick("Contact", "Contact")}
            </h2>
            <p className="mt-2 leading-7 text-gray-300">
              {pick("Pentru probleme legate de cont, plăți, date sau conținut, scrie-ne la", "For account, billing, data or content issues, contact us at")}{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="font-bold text-cyan-200 hover:text-white">
                {CONTACT_EMAIL}
              </a>
              .
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}

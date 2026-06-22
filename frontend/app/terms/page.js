"use client";

import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Crown,
  FileText,
  Scale,
  ShieldCheck,
  Trash2,
  UploadCloud,
  Wallet,
} from "lucide-react";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";

const CONTACT_EMAIL = "contact@cealeg.shop";

export default function TermsPage() {
  const { pick } = useLocale();

  const sections = [
    {
      icon: Scale,
      title: pick("Acceptarea termenilor", "Accepting the terms"),
      text: pick(
        "Prin crearea unui cont sau folosirea aplicatiei accepti acesti termeni si Politica de confidentialitate. Daca nu esti de acord, nu folosi serviciul.",
        "By creating an account or using the app, you accept these terms and the Privacy Policy. If you do not agree, do not use the service."
      ),
    },
    {
      icon: ShieldCheck,
      title: pick("Varsta minima", "Minimum age"),
      text: pick(
        "Pentru cont ai nevoie de cel putin 16 ani sau acordul parintelui/tutorelui. Nu folosim serviciul pentru a colecta intentionat date de la copii sub 13 ani.",
        "To create an account, you must be at least 16 or have parent/guardian consent. We do not use the service to knowingly collect data from children under 13."
      ),
    },
    {
      icon: AlertTriangle,
      title: pick("Nu este sfat medical", "Not medical advice"),
      text: pick(
        "Scorurile, verdicturile și alternativele sunt informative. Nu înlocuiesc sfatul medicului, nutriționistului, eticheta oficială, informațiile despre alergeni sau prețul afișat în magazin.",
        "Scores, verdicts and alternatives are informational. They do not replace advice from a doctor, nutritionist, official label, allergen information or the shelf price."
      ),
    },
    {
      icon: Wallet,
      title: pick("Abonamente si plati", "Subscriptions and payments"),
      text: pick(
        "Planurile plătite pot debloca scanări nelimitate și recomandări suplimentare. Plata este procesată prin Stripe. Prețurile, taxele și condițiile pot fi actualizate înainte de lansarea publică.",
        "Paid plans may unlock unlimited scans and extra recommendations. Payment is processed through Stripe. Prices, taxes and conditions may be updated before public launch."
      ),
    },
    {
      icon: Trash2,
      title: pick("Inchiderea contului", "Closing your account"),
      text: pick(
        "Poți cere ștergerea contului din dashboard. Pentru protecția ta, contul se șterge doar după confirmarea linkului trimis pe email. Dacă ai abonament activ, încercăm să îl anulăm înainte de ștergerea definitivă.",
        "You can request account deletion from the dashboard. For your protection, the account is deleted only after confirming the link sent by email. If you have an active subscription, we try to cancel it before final deletion."
      ),
    },
    {
      icon: UploadCloud,
      title: pick("Produse contribuite", "Contributed products"),
      text: pick(
        "Dacă încarci produse, imagini sau prețuri, confirmi că ai dreptul să le trimiți și că informațiile sunt corecte după cunoștința ta. Putem modera, corecta sau șterge contribuțiile.",
        "If you upload products, images or prices, you confirm that you have the right to submit them and that the information is accurate to your knowledge. We may moderate, correct or delete contributions."
      ),
    },
    {
      icon: FileText,
      title: pick("Utilizare corecta", "Fair use"),
      text: pick(
        "Nu încerca să ocolești limitele, să ataci API-ul, să încarci conținut ilegal, să copiezi masiv datele sau să folosești aplicația pentru activități abuzive.",
        "Do not try to bypass limits, attack the API, upload illegal content, scrape data at scale or use the app for abusive activity."
      ),
    },
  ];

  return (
    <main className="min-h-screen text-white">
      <section className="ce-shell-md ce-page">
        <div className="flex items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm font-bold text-emerald-300 hover:text-emerald-200"
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

        <div className="mt-10 rounded-2xl border border-white/10 bg-white/5 p-6 shadow-2xl md:p-8">
          <p className="flex items-center gap-2 text-sm font-bold text-emerald-300">
            <FileText size={17} /> {pick("Termeni si conditii", "Terms and conditions")}
          </p>
          <h1 className="mt-3 text-4xl font-black md:text-5xl">
            {pick("Reguli clare pentru folosirea aplicatiei.", "Clear rules for using the app.")}
          </h1>
          <p className="mt-4 max-w-3xl leading-8 text-gray-300">
            {pick(
              "Acesti termeni stabilesc cum poti folosi Ce aleg?, ce limitari exista si ce responsabilitati avem. Ultima actualizare: 5 iunie 2026.",
              "These terms define how you may use Ce aleg?, what limits apply and what responsibilities we have. Last updated: June 5, 2026."
            )}
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {sections.map(({ icon: Icon, title, text }) => (
              <section
                key={title}
                className="rounded-xl border border-white/10 bg-black/25 p-5"
              >
                <Icon className="text-emerald-300" size={21} />
                <h2 className="mt-3 text-lg font-black">{title}</h2>
                <p className="mt-2 leading-7 text-gray-300">{text}</p>
              </section>
            ))}
          </div>

          <div className="mt-8 rounded-xl border border-red-300/25 bg-red-300/10 p-5 text-red-100">
            <h2 className="font-black">
              {pick("Limitarea raspunderii", "Limitation of liability")}
            </h2>
            <p className="mt-2 leading-7">
              {pick(
                "Datele din surse publice pot fi incomplete, traduse greșit sau învechite. Folosești recomandările pe propria răspundere și trebuie să verifici produsul real înainte de cumpărare.",
                "Public-source data may be incomplete, mistranslated or outdated. You use recommendations at your own discretion and must verify the real product before purchase."
              )}
            </p>
          </div>

          <div className="mt-5 rounded-xl border border-white/10 bg-black/25 p-5">
            <h2 className="font-black">{pick("Contact", "Contact")}</h2>
            <p className="mt-2 leading-7 text-gray-300">
              {pick(
                "Pentru probleme legate de cont, plati, date sau continut, scrie-ne la",
                "For account, billing, data or content issues, contact us at"
              )}{" "}
              <a href={`mailto:${CONTACT_EMAIL}`} className="font-bold text-cyan-200 hover:text-white">
                {CONTACT_EMAIL}
              </a>
              .
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

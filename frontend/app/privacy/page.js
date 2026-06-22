"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Camera,
  Crown,
  Database,
  Mail,
  ShieldCheck,
  Trash2,
  UserCheck,
} from "lucide-react";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";

const CONTACT_EMAIL = "contact@cealeg.shop";

export default function PrivacyPage() {
  const { pick } = useLocale();

  const sections = [
    {
      icon: UserCheck,
      title: pick("Cine poate folosi aplicația", "Who can use the app"),
      text: pick(
        "Conturile sunt pentru persoane de cel puțin 16 ani sau pentru minori care folosesc aplicația cu acordul și supravegherea părintelui/tutorelui. Nu cerem în mod intenționat date de la copii sub 13 ani.",
        "Accounts are for people who are at least 16 years old, or for minors using the app with parent/guardian consent and supervision. We do not knowingly request data from children under 13."
      ),
    },
    {
      icon: Database,
      title: pick("Date pe care le pastram", "Data we keep"),
      text: pick(
        "Păstrăm datele necesare pentru cont, autentificare, coș, favorite, istoric de scanări, preferințe, abonament, produse contribuite și rapoarte de preț. Nu vindem date personale.",
        "We keep the data needed for your account, authentication, cart, favorites, scan history, preferences, subscription, contributed products and price reports. We do not sell personal data."
      ),
    },
    {
      icon: Camera,
      title: pick("Cameră, microfon și scanări", "Camera, microphone and scans"),
      text: pick(
        "Camera porneste doar dupa permisiunea ta. Cadrele folosite pentru identificare sunt procesate pentru a gasi produsul. Microfonul este folosit doar cand activezi o functie vocala.",
        "The camera starts only after you grant permission. Frames used for identification are processed to find the product. The microphone is used only when you enable a voice feature."
      ),
    },
    {
      icon: Mail,
      title: pick("Emailuri de cont", "Account emails"),
      text: pick(
        "Putem trimite emailuri pentru crearea contului, resetarea parolei, securitate și informații importante despre abonament. Emailurile de marketing vor fi separate și opționale.",
        "We may send emails for account creation, password reset, security and important subscription information. Marketing emails will be separate and optional."
      ),
    },
    {
      icon: ShieldCheck,
      title: pick("Securitate", "Security"),
      text: pick(
        "Folosim sesiuni semnate, parole hash-uite, limite de cereri si verificari pentru payload-uri mari sau invalide. Nicio protectie nu este perfecta, dar reducem expunerea datelor.",
        "We use signed sessions, hashed passwords, request limits and checks for oversized or invalid payloads. No protection is perfect, but we reduce data exposure."
      ),
    },
    {
      icon: Trash2,
      title: pick("Ștergere și acces", "Deletion and access"),
      text: pick(
        "Poți cere ștergerea contului din dashboard. Trimitem un email de confirmare, apoi ștergem contul și datele personale asociate care nu mai sunt necesare legal sau operațional. Pentru export de date, contactează-ne la emailul oficial al aplicației.",
        "You can request account deletion from the dashboard. We send a confirmation email, then delete the account and associated personal data that is no longer legally or operationally required. For data export, contact us at the official app email."
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
            <ShieldCheck size={17} /> {pick("Politica de confidentialitate", "Privacy policy")}
          </p>
          <h1 className="mt-3 text-4xl font-black md:text-5xl">
            {pick("Datele tale trebuie tratate serios.", "Your data must be treated seriously.")}
          </h1>
          <p className="mt-4 max-w-3xl leading-8 text-gray-300">
            {pick(
              "Această politică explică ce colectează Ce aleg?, de ce avem nevoie de aceste date și cum poți cere ștergerea lor. Ultima actualizare: 5 iunie 2026.",
              "This policy explains what Ce aleg? collects, why we need that data and how you can request deletion. Last updated: June 5, 2026."
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

          <div className="mt-8 rounded-xl border border-yellow-300/25 bg-yellow-300/10 p-5 text-yellow-100">
            <h2 className="font-black">
              {pick("Nota importanta", "Important note")}
            </h2>
            <p className="mt-2 leading-7">
              {pick(
                "Ce aleg? oferă informații orientative despre produse alimentare. Verifică mereu eticheta produsului, alergenii, prețul real și recomandările medicului dacă ai restricții alimentare.",
                "Ce aleg? provides informational guidance about food products. Always check the product label, allergens, real shelf price and medical advice if you have dietary restrictions."
              )}
            </p>
          </div>

          <div className="mt-5 rounded-xl border border-white/10 bg-black/25 p-5">
            <h2 className="font-black">{pick("Contact pentru date personale", "Personal data contact")}</h2>
            <p className="mt-2 leading-7 text-gray-300">
              {pick(
                "Pentru întrebări despre date, ștergere cont sau export, scrie-ne la",
                "For questions about data, account deletion or export, contact us at"
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

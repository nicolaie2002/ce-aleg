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

export default function PrivacyPage() {
  const { pick } = useLocale();

  const sections = [
    {
      icon: UserCheck,
      title: pick("Cine poate folosi aplicatia", "Who can use the app"),
      text: pick(
        "Conturile sunt pentru persoane de cel putin 16 ani sau pentru minori care folosesc aplicatia cu acordul si supravegherea parintelui/tutorelui. Nu cerem in mod intentionat date de la copii sub 13 ani.",
        "Accounts are for people who are at least 16 years old, or for minors using the app with parent/guardian consent and supervision. We do not knowingly request data from children under 13."
      ),
    },
    {
      icon: Database,
      title: pick("Date pe care le pastram", "Data we keep"),
      text: pick(
        "Pastram datele necesare pentru cont, autentificare, cos, favorite, istoric de scanari, preferinte, abonament, produse contribuite si rapoarte de pret. Nu vindem date personale.",
        "We keep the data needed for your account, authentication, cart, favorites, scan history, preferences, subscription, contributed products and price reports. We do not sell personal data."
      ),
    },
    {
      icon: Camera,
      title: pick("Camera, microfon si scanari", "Camera, microphone and scans"),
      text: pick(
        "Camera porneste doar dupa permisiunea ta. Cadrele folosite pentru identificare sunt procesate pentru a gasi produsul. Microfonul este folosit doar cand activezi o functie vocala.",
        "The camera starts only after you grant permission. Frames used for identification are processed to find the product. The microphone is used only when you enable a voice feature."
      ),
    },
    {
      icon: Mail,
      title: pick("Emailuri de cont", "Account emails"),
      text: pick(
        "Putem trimite emailuri pentru crearea contului, resetarea parolei, securitate si informatii importante despre abonament. Emailurile de marketing vor fi separate si optionale.",
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
      title: pick("Stergere si acces", "Deletion and access"),
      text: pick(
        "Poti cere stergerea contului din dashboard. Trimitem un email de confirmare, apoi stergem contul si datele personale asociate care nu mai sunt necesare legal sau operational. Pentru export de date, contacteaza-ne la emailul oficial al aplicatiei.",
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
            <ArrowLeft size={16} /> {pick("Pagina principala", "Home")}
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
              "Aceasta politica explica ce colecteaza Ce aleg?, de ce avem nevoie de aceste date si cum poti cere stergerea lor. Ultima actualizare: 5 iunie 2026.",
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
                "Ce aleg? ofera informatii orientative despre produse alimentare. Verifica mereu eticheta produsului, alergeni, pretul real si recomandarile medicului daca ai restrictii alimentare.",
                "Ce aleg? provides informational guidance about food products. Always check the product label, allergens, real shelf price and medical advice if you have dietary restrictions."
              )}
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

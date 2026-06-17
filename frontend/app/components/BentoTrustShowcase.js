"use client";

import Link from "next/link";
import { ArrowRight, BadgeCheck, BellRing, Camera, ChartNoAxesCombined, LockKeyhole, ScanLine, UsersRound } from "lucide-react";
import { InteractiveSurface } from "./InteractiveSurface";
import { useLocale } from "./LocaleProvider";

const tiles = [
  { className: "lg:col-span-4 lg:row-span-2", icon: ScanLine, titleRo: "Scanare rapida", titleEn: "Fast scanning", detailRo: "Cod de bare, cautare manuala si verificari vizuale intr-un singur flux.", detailEn: "Barcode, manual search and visual checks in one flow." },
  { className: "lg:col-span-2", icon: Camera, titleRo: "Camera live", titleEn: "Live camera", detailRo: "Potrivita pentru raft, fara meniuri tehnice inutile.", detailEn: "Built for the shelf, without technical menus." },
  { className: "lg:col-span-2 lg:row-span-2", icon: ChartNoAxesCombined, titleRo: "Verdict clar", titleEn: "Clear verdict", detailRo: "Scor, ingrediente si valori nutritionale usor de citit.", detailEn: "Score, ingredients and nutrition made readable." },
  { className: "lg:col-span-2", icon: LockKeyhole, titleRo: "Cont protejat", titleEn: "Protected account", detailRo: "Sesiuni, parole si actiuni sensibile protejate.", detailEn: "Sessions, passwords and sensitive actions protected." },
  { className: "lg:col-span-4 lg:row-span-2", icon: UsersRound, titleRo: "Profiluri Family", titleEn: "Family profiles", detailRo: "Preferinte separate pentru fiecare persoana din casa.", detailEn: "Separate preferences for every person at home." },
  { className: "lg:col-span-2 lg:row-span-2", icon: BellRing, titleRo: "Alerte utile", titleEn: "Useful alerts", detailRo: "Mesaje scurte, fara jargon si fara detalii pentru dezvoltatori.", detailEn: "Short messages without jargon or developer details." },
  { className: "lg:col-span-2", icon: BadgeCheck, titleRo: "Pregatit de lansare", titleEn: "Launch-ready", detailRo: "Stripe, Brevo, Supabase si domeniu conectate.", detailEn: "Stripe, Brevo, Supabase and domain connected." },
  { className: "lg:col-span-4", icon: ArrowRight, titleRo: "Recomandari dupa preferinte", titleEn: "Preference-based picks", detailRo: "Alternative ordonate dupa gust, buget si obiective.", detailEn: "Alternatives ranked by taste, budget and goals." },
];

export function BentoTrustShowcase() {
  const { pick } = useLocale();

  return (
    <section className="ce-bento-showcase border-y border-white/10">
      <div className="ce-shell ce-page">
        <div className="grid gap-8 xl:grid-cols-[420px_minmax(0,1fr)] xl:items-center">
          <div className="ce-reveal">
            <p className="text-sm font-black text-cyan-200">
              {pick("Experienta completa", "Complete experience")}
            </p>
            <h2 className="mt-3 text-4xl font-black leading-tight md:text-5xl">
              {pick("Un asistent de cumparaturi care se simte ca un produs real.", "A shopping assistant that feels like a real product.")}
            </h2>
            <p className="mt-4 leading-8 text-gray-300">
              {pick(
                "Fluxurile importante sunt la indemana: scanare, alternative, profiluri Family, cos si siguranta contului.",
                "The important flows stay close: scanning, alternatives, Family profiles, cart and account safety."
              )}
            </p>
            <Link
              href="/pricing"
              className="mt-7 inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
            >
              {pick("Vezi planurile", "See plans")}
              <ArrowRight size={18} />
            </Link>
          </div>

          <div className="ce-bento-grid">
            {tiles.map(({ className, icon: Icon, titleRo, titleEn, detailRo, detailEn }, index) => (
              <InteractiveSurface
                as="article"
                key={titleEn}
                className={`ce-bento-tile ce-reveal ce-reveal-delay-${Math.min(index + 1, 3)} ${className}`}
              >
                <span className="ce-bento-icon">
                  <Icon size={20} />
                </span>
                <h3>{pick(titleRo, titleEn)}</h3>
                <p>{pick(detailRo, detailEn)}</p>
              </InteractiveSurface>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

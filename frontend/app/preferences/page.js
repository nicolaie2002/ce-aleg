"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, ScanLine, SlidersHorizontal, UserRound } from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { FamilyProfiles } from "../components/FamilyProfiles";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";
import {
  clearProfilePreferences,
  getActiveProfile,
  readProfilePreferences,
  saveProfilePreferences,
} from "../utils/profilePreferences";

const criteria = [
  {
    id: "cheap",
    ro: "Mai ieftin",
    en: "Cheaper",
    detailRo: "Alege variante cu pret mai bun cand diferenta merita.",
    detailEn: "Prioritize better prices when the difference is worth it.",
  },
  {
    id: "protein",
    ro: "Mai multa proteina",
    en: "More protein",
    detailRo: "Bun pentru satietate, sport sau gustari mai consistente.",
    detailEn: "Good for satiety, fitness and more filling snacks.",
  },
  {
    id: "low_calorie",
    ro: "Mai putine calorii",
    en: "Fewer calories",
    detailRo: "Cauta optiuni mai usoare per 100g sau per portie.",
    detailEn: "Look for lighter options per 100g or serving.",
  },
  {
    id: "low_sugar",
    ro: "Mai putin zahar",
    en: "Less sugar",
    detailRo: "Reduce zaharul cand exista alternative apropiate.",
    detailEn: "Reduce sugar when close alternatives exist.",
  },
  {
    id: "vegan",
    ro: "De post",
    en: "Vegan",
    detailRo: "Preferinte pentru produse vegetale sau potrivite pentru post.",
    detailEn: "Prefer plant-based products.",
  },
  {
    id: "lactose_free",
    ro: "Fara lactoza",
    en: "Lactose-free",
    detailRo: "Evita lactoza cand exista optiuni potrivite.",
    detailEn: "Avoid lactose when suitable options exist.",
  },
  {
    id: "natural",
    ro: "Ingrediente mai curate",
    en: "Cleaner ingredients",
    detailRo: "Prioritizeaza liste de ingrediente mai scurte si mai clare.",
    detailEn: "Prioritize shorter, clearer ingredient lists.",
  },
  {
    id: "value",
    ro: "Raport calitate-pret",
    en: "Best value",
    detailRo: "Echilibreaza scorul, pretul si valorile nutritionale.",
    detailEn: "Balance score, price and nutrition.",
  },
];

export default function PreferencesPage() {
  const { pick, locale } = useLocale();
  const [selectedCriteria, setSelectedCriteria] = useState([]);
  const [request, setRequest] = useState("");
  const [saved, setSaved] = useState(false);
  const [activeProfile, setActiveProfileState] = useState(null);

  const selectedSummary = useMemo(
    () => criteria.filter((item) => selectedCriteria.includes(item.id)),
    [selectedCriteria]
  );

  function loadPreferencesForProfile(profile) {
    const savedPreferences = readProfilePreferences(profile?.id);

    if (!savedPreferences) {
      setSelectedCriteria([]);
      setRequest("");
      return;
    }

    setSelectedCriteria(Array.isArray(savedPreferences.criteria) ? savedPreferences.criteria : []);
    setRequest(savedPreferences.request || "");
  }

  useEffect(() => {
    queueMicrotask(() => {
      const profile = getActiveProfile();
      setActiveProfileState(profile);
      loadPreferencesForProfile(profile);
    });

    function handleProfileChange(event) {
      const profile = event.detail || getActiveProfile();
      setActiveProfileState(profile);
      loadPreferencesForProfile(profile);
      setSaved(false);
    }

    window.addEventListener("cealeg:profile-change", handleProfileChange);
    return () => window.removeEventListener("cealeg:profile-change", handleProfileChange);
  }, []);

  function toggleCriterion(id) {
    setSaved(false);
    setSelectedCriteria((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    );
  }

  function savePreferences() {
    saveProfilePreferences(activeProfile?.id, {
      profileId: activeProfile?.id || null,
      profileName: activeProfile?.name || "",
      criteria: selectedCriteria,
      request,
    });
    setSaved(true);
  }

  function resetPreferences() {
    setSelectedCriteria([]);
    setRequest("");
    clearProfilePreferences(activeProfile?.id);
    setSaved(false);
  }

  return (
    <main className="min-h-screen text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel={pick("Scaneaza codul", "Scan barcode")} />
      <section className="ce-shell ce-page">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white">
          <ArrowLeft size={16} /> {pick("Inapoi la dashboard", "Back to dashboard")}
        </Link>

        <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_430px]">
          <InteractiveSurface className="ce-panel ce-lifted-shell p-6 md:p-8">
            <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
              <SlidersHorizontal size={16} /> {pick("Preferinte de cumparare", "Shopping preferences")}
            </p>
            <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight md:text-5xl">
              {pick("Spune aplicatiei ce inseamna un produs mai bun.", "Tell the app what a better product means.")}
            </h1>
            <p className="mt-4 max-w-3xl leading-8 text-gray-300">
              {pick(
                "Aceste alegeri sunt folosite cand ceri alternative dupa scanare. Daca ai plan Family, fiecare membru isi pastreaza profilul separat.",
                "These choices are used when you ask for alternatives after scanning. With Family, every member keeps a separate profile."
              )}
            </p>

            <div className="mt-7 grid gap-3 sm:grid-cols-2">
              {criteria.map((item) => {
                const selected = selectedCriteria.includes(item.id);

                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => toggleCriterion(item.id)}
                    className={`rounded-xl border p-4 text-left transition hover:-translate-y-0.5 ${
                      selected
                        ? "border-cyan-200 bg-cyan-200 text-black shadow-[0_18px_38px_-28px_rgba(103,232,249,.7)]"
                        : "border-white/10 bg-white/[0.035] hover:border-cyan-200/45 hover:bg-white/[0.07]"
                    }`}
                  >
                    <span className="flex items-center justify-between gap-3">
                      <span className="font-black">{locale === "en" ? item.en : item.ro}</span>
                      {selected && <Check size={17} />}
                    </span>
                    <span className={`mt-2 block text-sm leading-6 ${selected ? "text-black/70" : "text-gray-400"}`}>
                      {locale === "en" ? item.detailEn : item.detailRo}
                    </span>
                  </button>
                );
              })}
            </div>

            <label className="mt-7 block text-sm font-bold text-gray-300">
              {pick("Cerinta personala", "Personal request")}
              <textarea
                value={request}
                onChange={(event) => {
                  setSaved(false);
                  setRequest(event.target.value);
                }}
                placeholder={pick(
                  "Ex: Vreau produse mai ieftine, cu putin zahar, dar sa nu fie foarte procesate.",
                  "Example: I want cheaper products with less sugar, but not highly processed options."
                )}
                className="mt-3 min-h-32 w-full rounded-xl border border-white/10 bg-black/25 p-4 text-white outline-none placeholder:text-gray-500 focus:border-cyan-300"
              />
            </label>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <button onClick={savePreferences} className="ce-premium-button rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100">
                {pick("Salveaza preferintele", "Save preferences")}
              </button>
              <button onClick={resetPreferences} className="rounded-lg border border-white/15 px-5 py-3 font-bold text-gray-200 hover:bg-white/10">
                {pick("Reseteaza", "Reset")}
              </button>
            </div>

            {saved && (
              <p className="mt-4 rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-4 text-sm text-cyan-100">
                {pick("Preferintele au fost salvate pentru profilul activ.", "Preferences were saved for the active profile.")}
              </p>
            )}
          </InteractiveSurface>

          <aside className="space-y-5">
            <FamilyProfiles compact />

            <InteractiveSurface className="rounded-2xl border border-white/10 bg-[#111923]/78 p-5 shadow-2xl backdrop-blur">
              <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
                <UserRound size={16} /> {pick("Profil activ", "Active profile")}
              </p>
              <h2 className="mt-2 text-2xl font-black">
                {activeProfile?.name || pick("Profil principal", "Main profile")}
              </h2>
              <div className="mt-4 flex flex-wrap gap-2">
                {selectedSummary.map((item) => (
                  <span key={item.id} className="inline-flex rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1 text-sm text-cyan-100">
                    {locale === "en" ? item.en : item.ro}
                  </span>
                ))}
                {!selectedSummary.length && (
                  <p className="text-sm leading-6 text-gray-400">
                    {pick("Nu ai selectat inca prioritati.", "No priorities selected yet.")}
                  </p>
                )}
              </div>
              {request && <p className="mt-5 rounded-xl border border-white/10 bg-black/24 p-4 text-sm leading-6 text-gray-300">{request}</p>}
              <Link href="/live-assistant" className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 font-black text-black hover:bg-cyan-100">
                <ScanLine size={17} />
                {pick("Testeaza cu asistentul live", "Try with live assistant")}
              </Link>
            </InteractiveSurface>
          </aside>
        </div>
      </section>
    </main>
  );
}

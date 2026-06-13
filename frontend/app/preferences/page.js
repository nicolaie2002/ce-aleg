"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, SlidersHorizontal } from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { useLocale } from "../components/LocaleProvider";

const criteria = [
  { id: "cheap", ro: "Mai ieftin", en: "Cheaper", detailRo: "Prioritizează produse cu preț mai bun.", detailEn: "Prioritize better priced products." },
  { id: "protein", ro: "Mai multă proteină", en: "More protein", detailRo: "Bun pentru sațietate și alimentație sportivă.", detailEn: "Good for satiety and fitness-oriented diets." },
  { id: "low_calorie", ro: "Mai puține calorii", en: "Fewer calories", detailRo: "Recomandări mai ușoare per 100g.", detailEn: "Lighter recommendations per 100g." },
  { id: "low_sugar", ro: "Mai puțin zahăr", en: "Less sugar", detailRo: "Reduce zahărul când există alternative.", detailEn: "Reduce sugar when alternatives exist." },
  { id: "vegan", ro: "De post", en: "Vegan", detailRo: "Caută variante vegetale sau potrivite pentru post.", detailEn: "Look for plant-based options." },
  { id: "lactose_free", ro: "Fără lactoză", en: "Lactose-free", detailRo: "Evită produsele cu lactoză când este posibil.", detailEn: "Avoid lactose when possible." },
  { id: "natural", ro: "Ingrediente mai curate", en: "Cleaner ingredients", detailRo: "Preferă liste de ingrediente mai simple.", detailEn: "Prefer simpler ingredient lists." },
  { id: "value", ro: "Best value", en: "Best value", detailRo: "Caută echilibrul dintre scor, preț și nutriție.", detailEn: "Balance score, price and nutrition." },
];

export default function PreferencesPage() {
  const { pick, locale } = useLocale();
  const [selectedCriteria, setSelectedCriteria] = useState([]);
  const [request, setRequest] = useState("");
  const [saved, setSaved] = useState(false);

  const selectedSummary = useMemo(
    () => criteria.filter((item) => selectedCriteria.includes(item.id)),
    [selectedCriteria]
  );

  useEffect(() => {
    queueMicrotask(() => {
      const savedPreferences = localStorage.getItem("cealeg_preferences");
      if (!savedPreferences) return;
      const parsed = JSON.parse(savedPreferences);
      setSelectedCriteria(Array.isArray(parsed.criteria) ? parsed.criteria : []);
      setRequest(parsed.request || "");
    });
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
    localStorage.setItem(
      "cealeg_preferences",
      JSON.stringify({
        criteria: selectedCriteria,
        request,
      })
    );
    setSaved(true);
  }

  function resetPreferences() {
    setSelectedCriteria([]);
    setRequest("");
    localStorage.removeItem("cealeg_preferences");
    setSaved(false);
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/live-assistant" actionLabel={pick("Asistent live", "Live assistant")} />
      <section className="ce-shell ce-page">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-bold text-emerald-300 hover:text-emerald-200">
          <ArrowLeft size={16} /> {pick("Înapoi la dashboard", "Back to dashboard")}
        </Link>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_360px]">
          <section className="rounded-lg border border-white/10 bg-white/5 p-6">
            <p className="flex items-center gap-2 text-sm font-bold text-emerald-300">
              <SlidersHorizontal size={16} /> {pick("Preferințe de cumpărare", "Shopping preferences")}
            </p>
            <h1 className="mt-3 text-4xl font-black">
              {pick("Spune aplicației ce înseamnă „mai bun” pentru tine.", "Tell the app what “better” means for you.")}
            </h1>
            <p className="mt-4 max-w-2xl text-gray-300">
              {pick(
                "Aceste setări sunt folosite automat când cauți alternative după un produs scanat.",
                "These settings are used automatically when you search for alternatives after scanning a product."
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
                    className={`rounded-lg border p-4 text-left ${
                      selected
                        ? "border-emerald-300 bg-emerald-400 text-black"
                        : "border-white/10 bg-black/30 hover:border-emerald-300/50 hover:bg-white/[0.07]"
                    }`}
                  >
                    <span className="flex items-center justify-between gap-3">
                      <span className="font-black">{locale === "en" ? item.en : item.ro}</span>
                      {selected && <Check size={17} />}
                    </span>
                    <span className={`mt-2 block text-sm ${selected ? "text-black/70" : "text-gray-400"}`}>
                      {locale === "en" ? item.detailEn : item.detailRo}
                    </span>
                  </button>
                );
              })}
            </div>

            <label className="mt-7 block text-sm font-bold text-gray-300">
              {pick("Instrucțiune personală", "Personal instruction")}
              <textarea
                value={request}
                onChange={(event) => {
                  setSaved(false);
                  setRequest(event.target.value);
                }}
                placeholder={pick(
                  "Ex: Vreau produse mai ieftine, fără mult zahăr, dar să nu fie variante foarte procesate.",
                  "Example: I want cheaper products with less sugar, but not highly processed options."
                )}
                className="mt-3 min-h-32 w-full rounded-lg border border-white/10 bg-black/30 p-4 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </label>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <button onClick={savePreferences} className="rounded-lg bg-emerald-400 px-5 py-3 font-black text-black hover:bg-emerald-300">
                {pick("Salvează preferințele", "Save preferences")}
              </button>
              <button onClick={resetPreferences} className="rounded-lg border border-white/15 px-5 py-3 font-bold text-gray-200 hover:bg-white/10">
                {pick("Resetează", "Reset")}
              </button>
            </div>

            {saved && (
              <p className="mt-4 rounded-lg border border-emerald-300/25 bg-emerald-400/10 p-4 text-sm text-emerald-100">
                {pick("Preferințele au fost salvate.", "Your preferences have been saved.")}
              </p>
            )}
          </section>

          <aside className="rounded-lg border border-white/10 bg-[#11171d] p-5">
            <p className="text-sm font-bold text-emerald-300">{pick("Profil activ", "Active profile")}</p>
            <div className="mt-4 space-y-2">
              {selectedSummary.map((item) => (
                <span key={item.id} className="inline-flex rounded-full border border-emerald-300/25 bg-emerald-400/10 px-3 py-1 text-sm text-emerald-100">
                  {locale === "en" ? item.en : item.ro}
                </span>
              ))}
              {!selectedSummary.length && <p className="text-sm text-gray-400">{pick("Nu ai selectat încă priorități.", "No priorities selected yet.")}</p>}
            </div>
            {request && <p className="mt-5 rounded-lg border border-white/10 bg-black/30 p-4 text-sm leading-6 text-gray-300">{request}</p>}
            <Link href="/live-assistant" className="mt-6 inline-flex w-full justify-center rounded-lg bg-emerald-400 px-4 py-3 font-black text-black hover:bg-emerald-300">
              {pick("Testează cu asistentul live", "Try with live assistant")}
            </Link>
          </aside>
        </div>
      </section>
    </main>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  BadgeDollarSign,
  CandyOff,
  Check,
  Flame,
  Leaf,
  MilkOff,
  RotateCcw,
  Save,
  ScanLine,
  Scale,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Sprout,
  Target,
  UserRound,
} from "lucide-react";
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
    icon: BadgeDollarSign,
    ro: "Mai ieftin",
    en: "Cheaper",
    detailRo: "Alege variante cu preț mai bun când diferența merită.",
    detailEn: "Prioritize better prices when the difference is worth it.",
  },
  {
    id: "protein",
    icon: BadgeCheck,
    ro: "Mai multă proteină",
    en: "More protein",
    detailRo: "Bun pentru sațietate, sport sau gustări mai consistente.",
    detailEn: "Good for satiety, fitness and more filling snacks.",
  },
  {
    id: "low_calorie",
    icon: Flame,
    ro: "Mai puține calorii",
    en: "Fewer calories",
    detailRo: "Caută opțiuni mai ușoare per 100g sau per porție.",
    detailEn: "Look for lighter options per 100g or serving.",
  },
  {
    id: "low_sugar",
    icon: CandyOff,
    ro: "Mai puțin zahăr",
    en: "Less sugar",
    detailRo: "Reduce zahărul când există alternative apropiate.",
    detailEn: "Reduce sugar when close alternatives exist.",
  },
  {
    id: "vegan",
    icon: Sprout,
    ro: "De post",
    en: "Vegan",
    detailRo: "Preferințe pentru produse vegetale sau potrivite pentru post.",
    detailEn: "Prefer plant-based products.",
  },
  {
    id: "lactose_free",
    icon: MilkOff,
    ro: "Fără lactoză",
    en: "Lactose-free",
    detailRo: "Evită lactoza când există opțiuni potrivite.",
    detailEn: "Avoid lactose when suitable options exist.",
  },
  {
    id: "natural",
    icon: Leaf,
    ro: "Ingrediente mai curate",
    en: "Cleaner ingredients",
    detailRo: "Prioritizează liste de ingrediente mai scurte și mai clare.",
    detailEn: "Prioritize shorter, clearer ingredient lists.",
  },
  {
    id: "value",
    icon: Scale,
    ro: "Raport calitate-preț",
    en: "Best value",
    detailRo: "Echilibrează scorul, prețul și valorile nutriționale.",
    detailEn: "Balance score, price and nutrition.",
  },
];

const goals = [
  {
    id: "balanced",
    icon: Target,
    ro: "Echilibru",
    en: "Balanced",
    detailRo: "Recomandări care combină scorul, ingredientele și valorile nutriționale.",
    detailEn: "Recommendations that balance score, ingredients and nutrition.",
  },
  {
    id: "budget",
    icon: BadgeDollarSign,
    ro: "Buget",
    en: "Budget",
    detailRo: "Prioritizează variante mai avantajoase când există prețuri comparabile.",
    detailEn: "Prioritize better value when comparable prices are available.",
  },
  {
    id: "fitness",
    icon: BadgeCheck,
    ro: "Proteină și sațietate",
    en: "Protein and satiety",
    detailRo: "Caută produse cu proteină mai bună și zahăr/calorii controlate.",
    detailEn: "Look for better protein with controlled sugar and calories.",
  },
  {
    id: "clean",
    icon: Leaf,
    ro: "Ingrediente simple",
    en: "Simple ingredients",
    detailRo: "Favorizează produse cu etichete mai scurte și mai ușor de înțeles.",
    detailEn: "Favor products with shorter, clearer labels.",
  },
];

const allergyOptions = [
  { id: "gluten", ro: "Gluten", en: "Gluten" },
  { id: "lactose", ro: "Lactoză", en: "Lactose" },
  { id: "peanuts", ro: "Arahide", en: "Peanuts" },
  { id: "nuts", ro: "Fructe cu coajă", en: "Tree nuts" },
  { id: "soy", ro: "Soia", en: "Soy" },
  { id: "egg", ro: "Ou", en: "Egg" },
  { id: "fish", ro: "Pește", en: "Fish" },
  { id: "sesame", ro: "Susan", en: "Sesame" },
];

export default function PreferencesPage() {
  const { pick, locale } = useLocale();
  const [selectedCriteria, setSelectedCriteria] = useState([]);
  const [selectedGoal, setSelectedGoal] = useState("balanced");
  const [selectedAllergies, setSelectedAllergies] = useState([]);
  const [avoidIngredients, setAvoidIngredients] = useState("");
  const [request, setRequest] = useState("");
  const [saved, setSaved] = useState(false);
  const [activeProfile, setActiveProfileState] = useState(null);

  const selectedSummary = useMemo(
    () => criteria.filter((item) => selectedCriteria.includes(item.id)),
    [selectedCriteria]
  );
  const activeGoal = goals.find((goal) => goal.id === selectedGoal) || goals[0];
  const selectedAllergyLabels = selectedAllergies
    .map((id) => allergyOptions.find((item) => item.id === id))
    .filter(Boolean);

  function loadPreferencesForProfile(profile) {
    const savedPreferences = readProfilePreferences(profile?.id);

    if (!savedPreferences) {
      setSelectedCriteria([]);
      setSelectedGoal("balanced");
      setSelectedAllergies([]);
      setAvoidIngredients("");
      setRequest("");
      return;
    }

    setSelectedCriteria(Array.isArray(savedPreferences.criteria) ? savedPreferences.criteria : []);
    setSelectedGoal(savedPreferences.goal || "balanced");
    setSelectedAllergies(Array.isArray(savedPreferences.allergies) ? savedPreferences.allergies : []);
    setAvoidIngredients(savedPreferences.avoidIngredients || "");
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

  function toggleAllergy(id) {
    setSaved(false);
    setSelectedAllergies((current) =>
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
      goal: selectedGoal,
      allergies: selectedAllergies,
      avoidIngredients,
      request,
    });
    setSaved(true);
  }

  function resetPreferences() {
    setSelectedCriteria([]);
    setSelectedGoal("balanced");
    setSelectedAllergies([]);
    setAvoidIngredients("");
    setRequest("");
    clearProfilePreferences(activeProfile?.id);
    setSaved(false);
  }

  return (
    <main className="min-h-screen text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel={pick("Scanează codul", "Scan barcode")} />
      <section className="ce-shell ce-page">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white">
          <ArrowLeft size={16} /> {pick("Înapoi la dashboard", "Back to dashboard")}
        </Link>

        <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_430px]">
          <InteractiveSurface className="ce-panel ce-lifted-shell p-6 md:p-8">
            <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
              <SlidersHorizontal size={16} /> {pick("Preferințe de cumpărare", "Shopping preferences")}
            </p>
            <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight md:text-5xl">
              {pick("Spune aplicației ce înseamnă un produs mai bun.", "Tell the app what a better product means.")}
            </h1>
            <p className="mt-4 max-w-3xl leading-8 text-gray-300">
              {pick(
                "Aceste alegeri sunt folosite când compari alternative după scanare. Pentru planul Family, fiecare membru își păstrează propriul profil.",
                "These choices are used when you ask for alternatives after scanning. With Family, every member keeps a separate profile."
              )}
            </p>

            <div className="mt-6 grid gap-3 md:grid-cols-3">
              <div className="ce-preference-card rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                <Sparkles className="h-5 w-5 text-cyan-200" />
                <p className="mt-3 font-black">{pick("Recomandări mai clare", "Clearer recommendations")}</p>
                <p className="mt-1 text-sm leading-6 text-gray-400">
                  {pick(
                    "Alternativele sunt ordonate după prioritățile tale, nu doar după scor.",
                    "Alternatives are ranked by your priorities, not only by score."
                  )}
                </p>
              </div>
              <div className="ce-preference-card rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                <ShieldCheck className="h-5 w-5 text-yellow-200" />
                <p className="mt-3 font-black">{pick("Filtre importante", "Important filters")}</p>
                <p className="mt-1 text-sm leading-6 text-gray-400">
                  {pick(
                    "Alergiile și ingredientele de evitat sunt tratate ca semnale de siguranță.",
                    "Allergies and avoided ingredients are treated as safety signals."
                  )}
                </p>
              </div>
              <div className="ce-preference-card rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                <UserRound className="h-5 w-5 text-cyan-200" />
                <p className="mt-3 font-black">{pick("Profil activ", "Active profile")}</p>
                <p className="mt-1 text-sm leading-6 text-gray-400">
                  {pick(
                    "Setările se aplică profilului selectat, ca recomandările să rămână personale.",
                    "Settings apply to the selected profile so recommendations stay personal."
                  )}
                </p>
              </div>
            </div>

            <div className="mt-7 rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
                <Target size={17} />
                {pick("Obiectiv principal", "Main goal")}
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {goals.map((goal) => {
                  const selected = selectedGoal === goal.id;
                  const Icon = goal.icon;

                  return (
                    <button
                      key={goal.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => {
                        setSaved(false);
                        setSelectedGoal(goal.id);
                      }}
                      className={`ce-preference-card rounded-xl border p-4 text-left transition hover:-translate-y-0.5 ${
                        selected
                          ? "border-cyan-200 bg-cyan-200 text-black shadow-[0_18px_38px_-28px_rgba(103,232,249,.7)]"
                          : "border-white/10 bg-white/[0.035] hover:border-cyan-200/45 hover:bg-white/[0.07]"
                      }`}
                    >
                      <span className="flex items-center justify-between gap-3">
                        <span className="flex items-center gap-2 font-black">
                          <Icon size={17} />
                          {locale === "en" ? goal.en : goal.ro}
                        </span>
                        {selected && <Check size={17} />}
                      </span>
                      <span className={`mt-2 block text-sm leading-6 ${selected ? "text-black/70" : "text-gray-400"}`}>
                        {locale === "en" ? goal.detailEn : goal.detailRo}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-7">
              <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
                <div>
                  <p className="text-sm font-black text-cyan-200">
                    {pick("Priorități pentru alternative", "Alternative priorities")}
                  </p>
                  <h2 className="mt-1 text-2xl font-black">
                    {pick("Alege ce contează când compari produse.", "Choose what matters when comparing products.")}
                  </h2>
                </div>
                <p className="max-w-sm text-sm leading-6 text-gray-400">
                  {pick(
                    "Poți combina mai multe criterii. Recomandările vor încerca să păstreze același tip de produs.",
                    "You can combine multiple criteria. Recommendations will try to stay in the same product type."
                  )}
                </p>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {criteria.map((item) => {
                const selected = selectedCriteria.includes(item.id);
                const Icon = item.icon;

                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggleCriterion(item.id)}
                    className={`ce-preference-card rounded-xl border p-4 text-left transition hover:-translate-y-0.5 ${
                      selected
                        ? "border-cyan-200 bg-cyan-200 text-black shadow-[0_18px_38px_-28px_rgba(103,232,249,.7)]"
                        : "border-white/10 bg-white/[0.035] hover:border-cyan-200/45 hover:bg-white/[0.07]"
                    }`}
                  >
                    <span className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 font-black">
                        <Icon size={17} />
                        {locale === "en" ? item.en : item.ro}
                      </span>
                      {selected && <Check size={17} />}
                    </span>
                    <span className={`mt-2 block text-sm leading-6 ${selected ? "text-black/70" : "text-gray-400"}`}>
                      {locale === "en" ? item.detailEn : item.detailRo}
                    </span>
                  </button>
                );
              })}
              </div>
            </div>

            <div className="mt-7 rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="flex items-center gap-2 text-sm font-black text-yellow-200">
                <AlertTriangle size={17} />
                {pick("Alergii și ingrediente de evitat", "Allergies and ingredients to avoid")}
              </p>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                {pick(
                  "Le folosim ca filtru de siguranță pentru alternative. Verifică totuși eticheta în magazin înainte să cumperi.",
                  "We use these as a safety filter for alternatives. Still check the label in store before buying."
                )}
              </p>

              <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {allergyOptions.map((item) => {
                  const selected = selectedAllergies.includes(item.id);

                  return (
                    <button
                      key={item.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => toggleAllergy(item.id)}
                      className={`rounded-lg border px-3 py-2 text-left text-sm font-black transition hover:-translate-y-0.5 ${
                        selected
                          ? "border-yellow-200 bg-yellow-200 text-black"
                          : "border-white/10 bg-white/[0.035] text-gray-200 hover:border-yellow-200/50"
                      }`}
                    >
                      {locale === "en" ? item.en : item.ro}
                    </button>
                  );
                })}
              </div>

              <label className="mt-4 block text-sm font-bold text-gray-300">
                {pick("Alte ingrediente de evitat", "Other ingredients to avoid")}
                <input
                  value={avoidIngredients}
                  onChange={(event) => {
                    setSaved(false);
                    setAvoidIngredients(event.target.value);
                  }}
                  placeholder={pick("Ex: palmier, aspartam, coloranți", "Example: palm oil, aspartame, colorants")}
                  className="mt-2 w-full rounded-xl border border-white/10 bg-black/25 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-cyan-300"
                />
              </label>
            </div>

            <label className="mt-7 block text-sm font-bold text-gray-300">
              {pick("Cerință personală", "Personal request")}
              <textarea
                value={request}
                onChange={(event) => {
                  setSaved(false);
                  setRequest(event.target.value);
                }}
                placeholder={pick(
                  "Ex: Vreau produse mai ieftine, cu puțin zahăr, dar să nu fie foarte procesate.",
                  "Example: I want cheaper products with less sugar, but not highly processed options."
                )}
                className="mt-3 min-h-32 w-full rounded-xl border border-white/10 bg-black/25 p-4 text-white outline-none placeholder:text-gray-500 focus:border-cyan-300"
              />
            </label>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <button onClick={savePreferences} className="ce-premium-button inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100">
                <Save size={17} />
                {pick("Salvează preferințele", "Save preferences")}
              </button>
              <button onClick={resetPreferences} className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-5 py-3 font-bold text-gray-200 hover:bg-white/10">
                <RotateCcw size={17} />
                {pick("Resetează", "Reset")}
              </button>
            </div>

            {saved && (
              <p role="status" aria-live="polite" className="mt-4 rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-4 text-sm text-cyan-100">
                {pick("Preferințele au fost salvate pentru profilul activ.", "Preferences were saved for the active profile.")}
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
              <p className="mt-3 inline-flex rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1 text-sm font-black text-cyan-100">
                {locale === "en" ? activeGoal.en : activeGoal.ro}
              </p>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-white/10 bg-black/22 p-3">
                  <p className="text-xs font-bold text-gray-400">{pick("Criterii", "Criteria")}</p>
                  <p className="mt-1 text-2xl font-black text-cyan-100">{selectedSummary.length}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/22 p-3">
                  <p className="text-xs font-bold text-gray-400">{pick("Alergii", "Allergies")}</p>
                  <p className="mt-1 text-2xl font-black text-yellow-100">{selectedAllergyLabels.length}</p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {selectedSummary.map((item) => (
                  <span key={item.id} className="inline-flex rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1 text-sm text-cyan-100">
                    {locale === "en" ? item.en : item.ro}
                  </span>
                ))}
                {selectedAllergyLabels.map((option) => (
                  <span key={option.id} className="inline-flex rounded-full border border-yellow-300/25 bg-yellow-300/10 px-3 py-1 text-sm text-yellow-100">
                    {locale === "en" ? option.en : option.ro}
                  </span>
                ))}
                {!selectedSummary.length && !selectedAllergies.length && (
                  <p className="text-sm leading-6 text-gray-400">
                    {pick("Nu ai selectat încă priorități.", "No priorities selected yet.")}
                  </p>
                )}
              </div>
              {avoidIngredients && (
                <p className="mt-4 rounded-xl border border-yellow-300/20 bg-yellow-300/10 p-4 text-sm leading-6 text-yellow-50">
                  {pick("Evită:", "Avoid:")} {avoidIngredients}
                </p>
              )}
              {request && <p className="mt-5 rounded-xl border border-white/10 bg-black/24 p-4 text-sm leading-6 text-gray-300">{request}</p>}
              <Link href="/barcode-scan" className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 font-black text-black hover:bg-cyan-100">
                <ScanLine size={17} />
                {pick("Scanează cu profilul activ", "Scan with active profile")}
              </Link>
            </InteractiveSurface>
          </aside>
        </div>
      </section>
    </main>
  );
}

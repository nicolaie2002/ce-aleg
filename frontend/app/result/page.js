"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  BadgeCheck,
  BadgeDollarSign,
  CandyOff,
  CheckCircle2,
  Flame,
  Heart,
  Leaf,
  Loader2,
  MilkOff,
  Search,
  ShoppingCart,
  Sprout,
  Zap,
} from "lucide-react";
import { API_URL } from "../config";
import { getImageUrl } from "../utils/getImageUrl";
import { getActiveProfile, getActiveProfilePayload, readProfilePreferences, saveProfilePreferences } from "../utils/profilePreferences";
import { ExpandableText } from "../components/ExpandableText";
import { ProductImage } from "../components/ProductImage";
import { AppHeader } from "../components/AppHeader";
import { useLocale } from "../components/LocaleProvider";
import { trackEvent } from "../utils/analytics";
import { getApiErrorMessage, localizeApiMessage, readApiJson } from "../utils/apiResponse";
import { localizeCatalogLabel } from "../catalog-romania/seo-data";

const criteriaOptions = [
  { id: "caffeine", ro: "Mai multă cofeină", en: "More caffeine", icon: Zap },
  { id: "cheap", ro: "Mai ieftin", en: "Lower price", icon: BadgeDollarSign },
  { id: "protein", ro: "Mai multă proteină", en: "More protein", icon: BadgeCheck },
  { id: "low_calorie", ro: "Mai puține calorii", en: "Fewer calories", icon: Flame },
  { id: "low_sugar", ro: "Mai puțin zahăr", en: "Less sugar", icon: CandyOff },
  { id: "vegan", ro: "De post", en: "Plant-based", icon: Sprout },
  { id: "lactose_free", ro: "Fără lactoză", en: "Lactose-free", icon: MilkOff },
  { id: "natural", ro: "Ingrediente mai simple", en: "Simpler ingredients", icon: Leaf },
  { id: "value", ro: "Raport calitate-preț", en: "Value for money", icon: BadgeCheck },
];

const emptyScannedProduct = {
  name: "",
  image: "",
  score: null,
  category: "",
  price: "preț necunoscut",
  calories: null,
  protein: null,
  sugar: null,
  fat: null,
  verdict: "Produs analizat pe bază informațiilor disponibile.",
  shortAdvice: "Produsul poate fi comparat cu alternative din aceeași categorie.",
};

const productReportReasons = [
  { id: "wrong_product", ro: "Produs greșit", en: "Wrong product" },
  { id: "wrong_price", ro: "Preț greșit", en: "Wrong price" },
  { id: "wrong_nutrition", ro: "Date nutriționale greșite", en: "Wrong nutrition data" },
  { id: "wrong_score", ro: "Scor sau verdict greșit", en: "Wrong score or verdict" },
  { id: "wrong_image", ro: "Imagine greșită", en: "Wrong image" },
  { id: "missing_data", ro: "Date incomplete", en: "Missing data" },
];

function hasNumericValue(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function formatNutritionValue(value, pick) {
  if (!hasNumericValue(value)) return pick("Indisponibil", "Unavailable");

  const number = Number(value);

  return number.toFixed(1).replace(/\.0$/, "");
}

function formatScore(value) {
  if (!hasNumericValue(value)) return "-";

  const number = Number(value);

  return number.toFixed(1).replace(/\.0$/, "");
}

function getPriceLabel(product, pick) {
  return product.price && product.price !== "preț necunoscut"
    ? product.price
    : pick("Verifică prețul în magazin", "Check the price in store");
}

function getStoreName(storeId, pick) {
  const stores = {
    lidl: "Lidl",
    kaufland: "Kaufland",
    carrefour: "Carrefour",
    mega: "Mega Image",
    profi: "Profi",
    penny: "Penny",
    local: pick("Magazin local", "Local store"),
    any: pick("Fără magazin ales", "No store selected"),
  };

  return stores[storeId] || pick("Fără magazin ales", "No store selected");
}

function ResultPageContent() {
  const { locale, pick } = useLocale();
  const searchParams = useSearchParams();
  const storeParam = searchParams.get("store") || "any";
  const storeName = getStoreName(storeParam, pick);

  const [user, setUser] = useState(null);
  const [selectedCriteria, setSelectedCriteria] = useState([]);
  const [customRequest, setCustomRequest] = useState("");
  const [addedToCart, setAddedToCart] = useState(false);
  const [addedToFavorites, setAddedToFavorites] = useState(false);
  const [isAddingToCart, setIsAddingToCart] = useState(false);
  const [isAddingToFavorites, setIsAddingToFavorites] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [scannedProduct, setScannedProduct] = useState(null);
  const [preferencesReady, setPreferencesReady] = useState(false);
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState("wrong_product");
  const [reportDetails, setReportDetails] = useState("");
  const [reportMessage, setReportMessage] = useState("");
  const [reportError, setReportError] = useState("");
  const [isReporting, setIsReporting] = useState(false);

  useEffect(() => {
    queueMicrotask(() => {
      const savedUser = localStorage.getItem("cealeg_user");

      if (savedUser) {
        setUser(JSON.parse(savedUser));
      }

      const savedResult = localStorage.getItem("cealeg_last_result");

      if (savedResult) {
        const parsedResult = JSON.parse(savedResult);

        if (parsedResult?.name && parsedResult.name !== "Produs demo") {
          setScannedProduct({
            ...emptyScannedProduct,
            ...parsedResult,
          });
        } else {
          localStorage.removeItem("cealeg_last_result");
        }
      }

      const activeProfile = getActiveProfile();
      const parsedPreferences = readProfilePreferences(activeProfile?.id);

      if (parsedPreferences) {
        setSelectedCriteria(parsedPreferences.criteria || []);
        setCustomRequest(parsedPreferences.request || "");
      }

      setPreferencesReady(true);
    });
  }, []);

  useEffect(() => {
    if (!preferencesReady) return;

    const activeProfile = getActiveProfile();
    saveProfilePreferences(activeProfile?.id, {
      profileId: activeProfile?.id || null,
      profileName: activeProfile?.name || "",
      criteria: selectedCriteria,
      request: customRequest,
    });
  }, [selectedCriteria, customRequest, preferencesReady]);

  function toggleCriteria(id) {
    if (selectedCriteria.includes(id)) {
      setSelectedCriteria(selectedCriteria.filter((item) => item !== id));
    } else {
      setSelectedCriteria([...selectedCriteria, id]);
    }
  }

  function buildAlternativeLink() {
    const criteria = selectedCriteria.join(",");
    const request = encodeURIComponent(customRequest);

    return `/alternatives?criteria=${criteria}&request=${request}&store=${storeParam}`;
  }

  if (!preferencesReady) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300" role="status">
          {pick("Se încarcă rezultatul...", "Loading result...")}
        </p>
      </main>
    );
  }

  if (!scannedProduct) {
    return (
      <main className="min-h-screen bg-[#0b0f14] text-white">
        <AppHeader actionHref="/barcode-scan" actionLabel={pick("Scanează produs", "Scan product")} />
        <section className="ce-shell-sm ce-page">
          <div className="rounded-3xl border border-white/10 bg-black/30 p-8 text-center shadow-2xl">
            <h1 className="text-3xl font-black">
              {pick("Nu există un rezultat de afișat.", "There is no result to display.")}
            </h1>
            <p className="mt-3 text-gray-300">
              {pick(
                "Scanează sau caută un produs ca să vezi analiza și alternativele.",
                "Scan or search for a product to see its analysis and alternatives."
              )}
            </p>
            <Link
              href={`/scan?store=${storeParam}`}
              className="mt-6 inline-flex rounded-2xl bg-emerald-400 px-6 py-3 font-black text-black hover:bg-emerald-300"
            >
              {pick("Scanează produsul", "Scan product")}
            </Link>
          </div>
        </section>
      </main>
    );
  }

  async function addScannedProductToCart() {
    if (isAddingToCart) return;

    if (!user) {
      window.location.assign("/login");
      return;
    }

    setErrorMessage("");
    setIsAddingToCart(true);

    try {
      const response = await fetch(`${API_URL}/cart/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          name: scannedProduct.name,
          store: storeName,
          score: scannedProduct.score,
          price: scannedProduct.price,
          image: scannedProduct.image,
          reason: scannedProduct.verdict,
          quantity: 1,
          ...getActiveProfilePayload(),
        }),
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(
            data,
            pick,
            "Nu s-a putut adăuga produsul în coș.",
            "The product could not be added to the cart."
          )
        );
      }

      setAddedToCart(true);
      window.dispatchEvent(new CustomEvent("cealeg:cart-updated"));
      setTimeout(() => setAddedToCart(false), 2500);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsAddingToCart(false);
    }
  }

  async function addScannedProductToFavorites() {
    if (isAddingToFavorites) return;

    if (!user) {
      window.location.assign("/login");
      return;
    }

    setErrorMessage("");
    setIsAddingToFavorites(true);

    try {
      const response = await fetch(`${API_URL}/favorites/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          name: scannedProduct.name,
          store: storeName,
          category: scannedProduct.category,
          score: scannedProduct.score,
          price: scannedProduct.price,
          image: scannedProduct.image,
          reason: scannedProduct.verdict,
        }),
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(
            data,
            pick,
            "Nu s-a putut salva produsul la favorite.",
            "The product could not be saved to favorites."
          )
        );
      }

      setAddedToFavorites(true);
      setTimeout(() => setAddedToFavorites(false), 2500);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsAddingToFavorites(false);
    }
  }

  async function reportScannedProduct() {
    if (isReporting || !scannedProduct) return;

    if (!user) {
      window.location.assign("/login?next=/result");
      return;
    }

    setReportMessage("");
    setReportError("");
    setIsReporting(true);

    try {
      const response = await fetch(`${API_URL}/feedback/product`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source: "result",
          store: storeName,
          reason: reportReason,
          details: reportDetails,
          product: {
            name: scannedProduct.name,
            barcode: scannedProduct.barcode,
            brand: scannedProduct.brand,
            category: scannedProduct.category,
            score: scannedProduct.score,
            price: scannedProduct.price,
            image: scannedProduct.image,
          },
        }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(
            data,
            pick,
            "Raportarea nu a putut fi trimisă.",
            "The report could not be sent."
          )
        );
      }

      setReportMessage(
        data.message
          ? localizeApiMessage(data.message, pick, data.code)
          : pick("Raportarea a fost trimisă.", "The report was sent.")
      );
      setReportDetails("");
      setIsReportOpen(false);
      trackEvent("product_report", {
        source: "result",
        reason: reportReason,
        category: scannedProduct.category,
      });
    } catch (error) {
      setReportError(
        error.message || pick("Raportarea nu a putut fi trimisă.", "The report could not be sent.")
      );
    } finally {
      setIsReporting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel={pick("Scanează din nou", "Scan again")} />
      <section className="ce-shell-lg ce-page">
          <Link
          href={`/scan?store=${storeParam}`}
          className="mb-8 inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
        >
          <ArrowLeft size={16} /> {pick("Înapoi la scanare", "Back to scanner")}
          </Link>

        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl">
          <div className="grid gap-6 md:grid-cols-[220px_1fr] md:items-center">
            <ProductImage
              src={getImageUrl(scannedProduct.image)}
              alt={scannedProduct.name}
              containerClassName="h-56 w-full rounded-3xl border border-white/10"
              imageClassName="object-contain p-4"
              fallbackClassName="text-5xl"
            />

            <div>
              <div className="flex flex-wrap gap-3">
                <p className="inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-300">
                  {pick("Rezultat analiză", "Analysis result")}
                </p>

                <p className="inline-flex rounded-full border border-white/10 bg-black/30 px-4 py-2 text-sm text-gray-300">
                  {storeName}
                </p>

                <p className="inline-flex rounded-full border border-white/10 bg-black/30 px-4 py-2 text-sm text-gray-300">
                  {localizeCatalogLabel(scannedProduct.category, locale)}
                </p>
              </div>

              <h1 className="mt-4 text-4xl font-bold">{scannedProduct.name}</h1>

              <ExpandableText
                text={scannedProduct.verdict}
                className="mt-3 max-w-2xl text-gray-300"
              />

              <div className="mt-5 flex flex-wrap items-center gap-4">
                <div className="flex h-28 w-28 items-center justify-center rounded-3xl bg-emerald-400 text-4xl font-black text-black">
                  {formatScore(scannedProduct.score)}
                </div>

                <div>
                  <p className="text-sm text-gray-400">{pick("Verdict general", "Overall verdict")}</p>
                  <p className="text-2xl font-bold text-emerald-300">
                    {hasNumericValue(scannedProduct.score)
                      ? pick("Bun, dar nu perfect", "Good, but not perfect")
                      : pick("Date în curs de completare", "Data is being completed")}
                  </p>
                  <p className="mt-1 text-sm text-gray-400">
                    {getPriceLabel(scannedProduct, pick)}
                  </p>
                  {scannedProduct.priceSource && (
                    <p className="mt-1 text-xs text-gray-500">
                      {[scannedProduct.priceStore, scannedProduct.priceDate]
                        .filter(Boolean)
                        .join(" · ")}{" "}
                      · Open Prices
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <button
                  onClick={addScannedProductToCart}
                  disabled={isAddingToCart}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-white px-6 py-4 text-center text-lg font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100 disabled:cursor-wait disabled:opacity-70"
                >
                  {isAddingToCart ? <Loader2 size={20} className="animate-spin" /> : <ShoppingCart size={20} />}
                  {isAddingToCart ? pick("Se adaugă...", "Adding...") : pick("Adaugă în coș", "Add to cart")}
                </button>

                <button
                  onClick={addScannedProductToFavorites}
                  disabled={isAddingToFavorites}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-yellow-300/30 px-6 py-4 text-center text-lg font-semibold text-yellow-300 transition hover:-translate-y-0.5 hover:bg-yellow-300/10 disabled:cursor-wait disabled:opacity-70"
                >
                  {isAddingToFavorites ? <Loader2 size={20} className="animate-spin" /> : <Heart size={20} />}
                  {isAddingToFavorites
                    ? pick("Se salvează...", "Saving...")
                    : pick("Adaugă la favorite", "Add to favorites")}
                </button>

          <Link
                  href="/cart"
                  className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-6 py-4 text-center text-lg font-semibold text-white transition hover:-translate-y-0.5 hover:bg-white/10"
                >
                  <ShoppingCart size={20} />
                  {pick("Vezi coșul", "View cart")}
          </Link>
              </div>

              {addedToCart && (
                <div role="status" className="mt-4 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-300">
                  {pick("Produsul scanat a fost adăugat în coș.", "The scanned product was added to the cart.")}
                </div>
              )}

              {addedToFavorites && (
                <div role="status" className="mt-4 rounded-2xl border border-yellow-300/30 bg-yellow-300/10 p-4 text-yellow-300">
                  {pick("Produsul a fost salvat la favorite.", "The product was saved to favorites.")}
                </div>
              )}

              {errorMessage && (
                <div role="alert" className="mt-4 rounded-2xl border border-red-400/30 bg-red-400/10 p-4 text-red-300">
                  {errorMessage}
                </div>
              )}

              <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="inline-flex items-center gap-2 text-sm font-black text-yellow-100">
                      <AlertTriangle size={16} />
                      {pick("Ai observat o problemă?", "Found a problem?")}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-gray-400">
                      {pick(
                        "Trimite problema pentru ca produsul să fie corectat rapid.",
                        "Send the issue so the product can be corrected quickly."
                      )}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setIsReportOpen((value) => !value);
                      setReportError("");
                    }}
                    className="inline-flex items-center justify-center gap-2 rounded-xl border border-yellow-300/30 px-4 py-3 text-sm font-black text-yellow-100 hover:bg-yellow-300/10"
                  >
                    <AlertTriangle size={16} />
                    {pick("Raportează", "Report")}
                  </button>
                </div>

                {isReportOpen && (
                  <div className="mt-4 border-t border-white/10 pt-4">
                    <div className="grid gap-2 sm:grid-cols-2">
                      {productReportReasons.map((reason) => (
                        <button
                          key={reason.id}
                          type="button"
                          onClick={() => setReportReason(reason.id)}
                          aria-pressed={reportReason === reason.id}
                          className={`rounded-xl border px-3 py-3 text-left text-sm font-black transition ${
                            reportReason === reason.id
                              ? "border-yellow-300 bg-yellow-300 text-black"
                              : "border-white/10 bg-white/[0.035] text-gray-200 hover:bg-white/10"
                          }`}
                        >
                          {pick(reason.ro, reason.en)}
                        </button>
                      ))}
                    </div>
                    <textarea
                      value={reportDetails}
                      onChange={(event) => setReportDetails(event.target.value)}
                      aria-label={pick("Detalii despre problemă", "Problem details")}
                      placeholder={pick(
                        "Opțional: ce este greșit? Exemplu: prețul este 6,99 lei, nu 9,99.",
                        "Optional: what is wrong? Example: the price is 6.99, not 9.99."
                      )}
                      className="mt-3 min-h-24 w-full rounded-xl border border-white/10 bg-black/35 p-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-yellow-300"
                    />
                    <button
                      type="button"
                      onClick={reportScannedProduct}
                      disabled={isReporting}
                      className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-yellow-300 px-4 py-3 text-sm font-black text-black hover:bg-yellow-200 disabled:cursor-wait disabled:opacity-60 sm:w-auto"
                    >
                      {isReporting ? <Loader2 size={17} className="animate-spin" /> : <CheckCircle2 size={17} />}
                      {isReporting ? pick("Se trimite...", "Sending...") : pick("Trimite raportarea", "Send report")}
                    </button>
                  </div>
                )}

                {reportMessage && (
                  <p role="status" className="mt-3 rounded-xl border border-emerald-300/25 bg-emerald-400/10 p-3 text-sm font-bold text-emerald-100">
                    {reportMessage}
                  </p>
                )}
                {reportError && (
                  <p role="alert" className="mt-3 rounded-xl border border-red-400/25 bg-red-400/10 p-3 text-sm font-bold text-red-100">
                    {reportError}
                  </p>
                )}
              </div>
            </div>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-4">
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Proteină", "Protein")}</p>
              <p className="mt-1 text-xl font-bold text-emerald-300">
                {formatNutritionValue(scannedProduct.protein, pick)}
                {hasNumericValue(scannedProduct.protein) ? "g / 100g" : ""}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Zahăr", "Sugar")}</p>
              <p className="mt-1 text-xl font-bold text-yellow-300">
                {formatNutritionValue(scannedProduct.sugar, pick)}
                {hasNumericValue(scannedProduct.sugar) ? "g / 100g" : ""}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Calorii", "Calories")}</p>
              <p className="mt-1 text-xl font-bold text-yellow-300">
                {formatNutritionValue(scannedProduct.calories, pick)}
                {hasNumericValue(scannedProduct.calories) ? " kcal" : ""}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Grăsimi", "Fat")}</p>
              <p className="mt-1 text-xl font-bold text-emerald-300">
                {formatNutritionValue(scannedProduct.fat, pick)}
                {hasNumericValue(scannedProduct.fat) ? "g / 100g" : ""}
              </p>
            </div>
          </div>

          <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-5">
            <h2 className="text-xl font-bold">{pick("Verdict rapid", "Quick verdict")}</h2>
            <ExpandableText
              text={scannedProduct.shortAdvice}
              className="mt-3 text-gray-300"
            />
          </div>

          <div className="mt-8 rounded-3xl border border-white/10 bg-black/30 p-5">
            <h2 className="text-2xl font-bold">{pick("Ce alternativă cauți?", "What alternative are you looking for?")}</h2>

            <p className="mt-2 text-gray-400">
              {pick(
                "Alege una sau mai multe opțiuni. Le vom folosi împreună cu magazinul selectat și le vom păstra pentru următoarele scanări.",
                "Choose one or more options. We will use them with the selected store and save them for future scans."
              )}
            </p>

            <div className="mt-5 grid gap-3 sm:grid-cols-2 md:grid-cols-4">
              {criteriaOptions.map((option) => {
                const selected = selectedCriteria.includes(option.id);
                const Icon = option.icon;

                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => toggleCriteria(option.id)}
                    aria-pressed={selected}
                    className={`rounded-2xl border px-4 py-4 text-left transition ${
                      selected
                        ? "border-emerald-400 bg-emerald-400 text-black"
                        : "border-white/10 bg-white/5 hover:border-emerald-400/50 hover:bg-white/10"
                    }`}
                  >
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
                      <Icon size={22} />
                    </span>
                    <span className="mt-2 block text-sm font-bold">
                      {pick(option.ro, option.en)}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="mt-6">
              <label htmlFor="result-custom-request" className="text-sm font-semibold text-gray-300">
                {pick("Sau scrie exact ce vrei:", "Or describe exactly what you want:")}
              </label>

              <textarea
                id="result-custom-request"
                value={customRequest}
                onChange={(e) => setCustomRequest(e.target.value)}
                placeholder={pick(
                  "Exemplu: vreau ceva de post, mai ieftin și cu mai puțin zahăr.",
                  "Example: I want something plant-based, cheaper and lower in sugar."
                )}
                className="mt-3 min-h-28 w-full rounded-2xl border border-white/10 bg-white/5 p-4 text-white outline-none transition placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <Link
              href={buildAlternativeLink()}
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-6 py-4 text-center text-lg font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
            >
              <Search size={20} />
              {pick("Caută alternative potrivite", "Find suitable alternatives")}
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

export default function ResultPage() {
  return (
    <Suspense fallback={null}>
      <ResultPageContent />
    </Suspense>
  );
}

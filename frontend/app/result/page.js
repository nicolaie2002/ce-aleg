"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { API_URL } from "../config";
import { getImageUrl } from "../utils/getImageUrl";
import { getActiveProfile, readProfilePreferences, saveProfilePreferences } from "../utils/profilePreferences";
import { ExpandableText } from "../components/ExpandableText";
import { ProductImage } from "../components/ProductImage";
import { AppHeader } from "../components/AppHeader";

const criteriaOptions = [
  { id: "caffeine", label: "Mai multa cafeina", icon: "⚡" },
  { id: "cheap", label: "Mai ieftin", icon: "💸" },
  { id: "protein", label: "Mai multă proteină", icon: "💪" },
  { id: "low_calorie", label: "Mai puține calorii", icon: "🔥" },
  { id: "low_sugar", label: "Mai puțin zahăr", icon: "🍬" },
  { id: "vegan", label: "De post", icon: "🌱" },
  { id: "lactose_free", label: "Fără lactoză", icon: "🥛" },
  { id: "natural", label: "Ingrediente mai curate", icon: "🌿" },
  { id: "value", label: "Best value", icon: "⭐" },
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
  verdict: "Produs analizat pe baza informațiilor disponibile.",
  shortAdvice: "Produsul poate fi comparat cu alternative din aceeași categorie.",
};

function hasNumericValue(value) {
  return (
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value))
  );
}

function formatNutritionValue(value) {
  if (!hasNumericValue(value)) return "Indisponibil";

  const number = Number(value);

  return number.toFixed(1).replace(/\.0$/, "");
}

function formatScore(value) {
  if (!hasNumericValue(value)) return "-";

  const number = Number(value);

  return number.toFixed(1).replace(/\.0$/, "");
}

function getPriceLabel(product) {
  return product.price && product.price !== "preț necunoscut"
    ? product.price
    : "Verifică prețul în magazin";
}

function getStoreName(storeId) {
  const stores = {
    lidl: "Lidl",
    kaufland: "Kaufland",
    carrefour: "Carrefour",
    mega: "Mega Image",
    profi: "Profi",
    penny: "Penny",
    local: "Market local",
    any: "Fără magazin ales",
  };

  return stores[storeId] || "Fără magazin ales";
}

function ResultPageContent() {
  const searchParams = useSearchParams();
  const storeParam = searchParams.get("store") || "any";
  const storeName = getStoreName(storeParam);

  const [user, setUser] = useState(null);
  const [selectedCriteria, setSelectedCriteria] = useState([]);
  const [customRequest, setCustomRequest] = useState("");
  const [addedToCart, setAddedToCart] = useState(false);
  const [addedToFavorites, setAddedToFavorites] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [scannedProduct, setScannedProduct] = useState(null);
  const [preferencesReady, setPreferencesReady] = useState(false);

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
        <p className="text-gray-300">Se incarca rezultatul...</p>
      </main>
    );
  }

  if (!scannedProduct) {
    return (
      <main className="min-h-screen bg-[#0b0f14] text-white">
        <AppHeader actionHref="/barcode-scan" actionLabel="Scaneaza produs" />
        <section className="ce-shell-sm ce-page">
          <div className="rounded-3xl border border-white/10 bg-black/30 p-8 text-center shadow-2xl">
            <h1 className="text-3xl font-black">Nu exista un rezultat de afisat.</h1>
            <p className="mt-3 text-gray-300">
              Scaneaza sau cauta un produs ca sa vezi analiza si alternativele.
            </p>
            <Link
              href={`/scan?store=${storeParam}`}
              className="mt-6 inline-flex rounded-2xl bg-emerald-400 px-6 py-3 font-black text-black hover:bg-emerald-300"
            >
              Scaneaza produsul
            </Link>
          </div>
        </section>
      </main>
    );
  }

  async function addScannedProductToCart() {
    if (!user) {
      window.location.assign("/login");
      return;
    }

    setErrorMessage("");

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
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut adăuga produsul în coș.");
      }

      setAddedToCart(true);
      setTimeout(() => setAddedToCart(false), 2500);
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  async function addScannedProductToFavorites() {
    if (!user) {
      window.location.assign("/login");
      return;
    }

    setErrorMessage("");

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

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut salva produsul la favorite.");
      }

      setAddedToFavorites(true);
      setTimeout(() => setAddedToFavorites(false), 2500);
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel="Scanează din nou" />
      <section className="ce-shell-lg ce-page">
          <Link
          href={`/scan?store=${storeParam}`}
          className="mb-8 inline-block text-sm text-emerald-300 hover:text-emerald-200"
        >
          ← Înapoi la scanare
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
                  Rezultat analiză
                </p>

                <p className="inline-flex rounded-full border border-white/10 bg-black/30 px-4 py-2 text-sm text-gray-300">
                  {storeName}
                </p>

                <p className="inline-flex rounded-full border border-white/10 bg-black/30 px-4 py-2 text-sm text-gray-300">
                  {scannedProduct.category}
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
                  <p className="text-sm text-gray-400">Verdict general</p>
                  <p className="text-2xl font-bold text-emerald-300">
                    {hasNumericValue(scannedProduct.score)
                      ? "Bun, dar nu perfect"
                      : "Date în curs de completare"}
                  </p>
                  <p className="mt-1 text-sm text-gray-400">
                    {getPriceLabel(scannedProduct)}
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
                  className="rounded-2xl bg-emerald-400 px-6 py-4 text-center text-lg font-semibold text-black transition hover:bg-emerald-300"
                >
                  Adaugă în coș
                </button>

                <button
                  onClick={addScannedProductToFavorites}
                  className="rounded-2xl border border-yellow-300/30 px-6 py-4 text-center text-lg font-semibold text-yellow-300 transition hover:bg-yellow-300/10"
                >
                  Adaugă la favorite ⭐
                </button>

          <Link
                  href="/cart"
                  className="rounded-2xl border border-white/10 px-6 py-4 text-center text-lg font-semibold text-white transition hover:bg-white/10"
                >
                  Vezi coșul 🛒
          </Link>
              </div>

              {addedToCart && (
                <div className="mt-4 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-300">
                  Produsul scanat a fost adăugat în coș.
                </div>
              )}

              {addedToFavorites && (
                <div className="mt-4 rounded-2xl border border-yellow-300/30 bg-yellow-300/10 p-4 text-yellow-300">
                  Produsul a fost salvat la favorite.
                </div>
              )}

              {errorMessage && (
                <div className="mt-4 rounded-2xl border border-red-400/30 bg-red-400/10 p-4 text-red-300">
                  {errorMessage}
                </div>
              )}
            </div>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-4">
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">Proteină</p>
              <p className="mt-1 text-xl font-bold text-emerald-300">
                {formatNutritionValue(scannedProduct.protein)}
                {hasNumericValue(scannedProduct.protein) ? "g / 100g" : ""}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">Zahăr</p>
              <p className="mt-1 text-xl font-bold text-yellow-300">
                {formatNutritionValue(scannedProduct.sugar)}
                {hasNumericValue(scannedProduct.sugar) ? "g / 100g" : ""}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">Calorii</p>
              <p className="mt-1 text-xl font-bold text-yellow-300">
                {formatNutritionValue(scannedProduct.calories)}
                {hasNumericValue(scannedProduct.calories) ? " kcal" : ""}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">Grăsimi</p>
              <p className="mt-1 text-xl font-bold text-emerald-300">
                {formatNutritionValue(scannedProduct.fat)}
                {hasNumericValue(scannedProduct.fat) ? "g / 100g" : ""}
              </p>
            </div>
          </div>

          <div className="mt-8 rounded-2xl border border-white/10 bg-black/30 p-5">
            <h2 className="text-xl font-bold">Verdict rapid</h2>
            <ExpandableText
              text={scannedProduct.shortAdvice}
              className="mt-3 text-gray-300"
            />
          </div>

          <div className="mt-8 rounded-3xl border border-white/10 bg-black/30 p-5">
            <h2 className="text-2xl font-bold">Ce alternativă cauți?</h2>

            <p className="mt-2 text-gray-400">
              Alege una sau mai multe opțiuni. Aplicația va folosi aceste
              criterii împreună cu magazinul selectat și le va păstra pentru
              următoarele scanări.
            </p>

            <div className="mt-5 grid gap-3 sm:grid-cols-2 md:grid-cols-4">
              {criteriaOptions.map((option) => {
                const selected = selectedCriteria.includes(option.id);

                return (
                  <button
                    key={option.id}
                    onClick={() => toggleCriteria(option.id)}
                    className={`rounded-2xl border px-4 py-4 text-left transition ${
                      selected
                        ? "border-emerald-400 bg-emerald-400 text-black"
                        : "border-white/10 bg-white/5 hover:border-emerald-400/50 hover:bg-white/10"
                    }`}
                  >
                    <span className="text-2xl">{option.icon}</span>
                    <span className="mt-2 block text-sm font-bold">
                      {option.label}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="mt-6">
              <label className="text-sm font-semibold text-gray-300">
                Sau scrie exact ce vrei:
              </label>

              <textarea
                value={customRequest}
                onChange={(e) => setCustomRequest(e.target.value)}
                placeholder="Ex: Vreau ceva de post, mai ieftin și cu mai puțin zahăr."
                className="mt-3 min-h-28 w-full rounded-2xl border border-white/10 bg-white/5 p-4 text-white outline-none transition placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <Link
              href={buildAlternativeLink()}
              className="mt-6 block rounded-2xl bg-emerald-400 px-6 py-4 text-center text-lg font-semibold text-black transition hover:bg-emerald-300"
            >
              Caută alternative potrivite
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

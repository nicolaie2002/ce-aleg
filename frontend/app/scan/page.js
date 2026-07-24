"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Barcode,
  Camera,
  CheckCircle2,
  Clock3,
  ImagePlus,
  Info,
  Loader2,
  Search,
  Sparkles,
} from "lucide-react";
import { API_URL } from "../config";
import { ProductImage } from "../components/ProductImage";
import { AppHeader } from "../components/AppHeader";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";
import { getApiErrorMessage, readApiJson } from "../utils/apiResponse";
import { localizeCatalogLabel } from "../catalog-romania/seo-data";

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

function getImageUrl(path) {
  if (!path) return "";

  if (path.startsWith("http")) {
    return path;
  }

  if (path.startsWith("/uploads")) {
    return `${API_URL}${path}`;
  }

  return path;
}

function ScanPageContent() {
  const { locale, pick } = useLocale();
  const searchParams = useSearchParams();
  const storeParam = searchParams.get("store") || "any";
  const storeName = getStoreName(storeParam, pick);

  const [user, setUser] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [productQuery, setProductQuery] = useState("");
  const [unknownProduct, setUnknownProduct] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [isReadingLabel, setIsReadingLabel] = useState(false);
  const [detectedLabelText, setDetectedLabelText] = useState("");

  useEffect(() => {
    queueMicrotask(() => {
      const savedUser = localStorage.getItem("cealeg_user");

      if (!savedUser) {
        window.location.assign("/login");
        return;
      }

      setUser(JSON.parse(savedUser));
    });
  }, []);

  useEffect(() => {
    if (!imagePreview) return undefined;

    return () => {
      URL.revokeObjectURL(imagePreview);
    };
  }, [imagePreview]);

  function extractProductHint(text) {
    const ignoredTerms = [
      "ingrediente",
      "ingredients",
      "nutrition",
      "nutritional",
      "valoare energetica",
      "grasimi",
      "zahar",
      "proteine",
      "protein",
      "carbohidrati",
      "calorii",
      "kcal",
      "100g",
      "100ml",
    ];

    const usefulLines = text
      .split(/\r?\n/)
      .map((line) => line.replace(/\s+/g, " ").trim())
      .filter((line) => {
        const normalized = line.toLowerCase();
        const letterCount = (line.match(/[a-zA-Z]/g) || []).length;

        return (
          line.length >= 3 &&
          line.length <= 55 &&
          letterCount >= 3 &&
          !ignoredTerms.some((term) => normalized.includes(term)) &&
          !/^[\d\s.,%:/-]+$/.test(line)
        );
      })
      .sort((first, second) => {
        const firstScore =
          (/[A-Z]{3,}/.test(first) ? 12 : 0) +
          Math.min(first.length, 30);
        const secondScore =
          (/[A-Z]{3,}/.test(second) ? 12 : 0) +
          Math.min(second.length, 30);

        return secondScore - firstScore;
      });

    return [...new Set(usefulLines)].slice(0, 2).join(" ").trim();
  }

  async function readLabelFromImage(file) {
    setIsReadingLabel(true);
    setDetectedLabelText("");

    try {
      const { createWorker } = await import("tesseract.js");
      const worker = await createWorker("eng");

      try {
        const result = await worker.recognize(file);
        const hint = extractProductHint(result.data.text || "");

        if (hint) {
          setDetectedLabelText(hint);
          setProductQuery((currentQuery) => currentQuery.trim() || hint);
        }
      } finally {
        await worker.terminate();
      }
    } catch (error) {
      console.warn("Eticheta nu a putut fi citita local.", error);
    } finally {
      setIsReadingLabel(false);
    }
  }

  function handleImageUpload(event) {
    const file = event.target.files[0];

    if (file) {
      const imageUrl = URL.createObjectURL(file);
      setImagePreview(imageUrl);
      setSelectedFile(file);
      setErrorMessage("");
      setSearchError("");
      setUnknownProduct(null);
      setSelectedSuggestion(null);
      void readLabelFromImage(file);
    }
  }

  useEffect(() => {
    const queryText = productQuery.trim();
    let isActive = true;
    const controller = new AbortController();

    const timer = setTimeout(async () => {
      if (selectedSuggestion?.name === queryText) {
        setSuggestions([]);
        setSearchError("");
        return;
      }

      if (queryText.length < 3) {
        setSuggestions([]);
        setSearchError("");
        return;
      }

      setIsSearching(true);
      setSearchError("");

      try {
        const response = await fetch(
          `${API_URL}/products/search?q=${encodeURIComponent(
            queryText
          )}&store=${encodeURIComponent(storeParam)}${
            user?.id ? `&user_id=${encodeURIComponent(user.id)}` : ""
          }`,
          { signal: controller.signal }
        );

        const data = await readApiJson(response);

        if (!response.ok) {
          throw new Error(getApiErrorMessage(data, pick, "Nu s-au putut încărca sugestiile.", "Suggestions could not be loaded."));
        }

        if (isActive) {
          setSuggestions(data);
          setSearchError("");
        }
      } catch (error) {
        if (error.name === "AbortError") {
          return;
        }

        console.error(error);

        if (isActive) {
          setSuggestions([]);
          setSearchError(
            error.message || pick("Catalogul extern nu răspunde acum. Încearcă din nou în câteva clipe.", "The external catalog is not responding. Try again in a few moments.")
          );
        }
      } finally {
        if (isActive) {
          setIsSearching(false);
        }
      }
    }, queryText.length < 3 ? 0 : 600);

    return () => {
      isActive = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [pick, productQuery, selectedSuggestion, storeParam, user?.id]);

  function selectSuggestion(product) {
    setSelectedSuggestion(product);
    setProductQuery(product.name);
    setSuggestions([]);
    setUnknownProduct(null);
    setErrorMessage("");
    setSearchError("");
  }

  function buildResultFromSuggestion(product) {
    const fallbackReason = pick(
      "Produs găsit în catalogul online. Verifică eticheta de pe ambalaj înainte de cumpărare și compară alternativele din aceeași categorie.",
      "Product found in the online catalog. Check the package label before buying and compare alternatives in the same category."
    );

    return {
      id: product.id || null,
      barcode: product.barcode || null,
      name: product.name,
      brand: product.brand || "",
      store: storeName,
      source: product.source || "catalog",
      score: product.score,
      category: product.category || pick("Categorie neconfirmată", "Unconfirmed category"),
      price: product.priceText || product.price || pick("Verifică prețul în magazin", "Check the price in store"),
      calories: product.calories,
      protein: product.protein,
      sugar: product.sugar,
      fat: product.fat,
      image: product.image || "",
      verdict: product.reason || fallbackReason,
      shortAdvice: product.reason || fallbackReason,
      ingredients: product.ingredients || "",
      searchedText: productQuery.trim(),
      confirmedSuggestion: true,
    };
  }

  async function saveScanToBackend(result) {
    if (!user) return;

    await fetch(`${API_URL}/history/add`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user.id,
        name: result.name,
        store: storeName,
        category: result.category,
        score: result.score,
        price: result.price,
        image: result.image,
        verdict: result.verdict,
        shortAdvice: result.shortAdvice,
      }),
    });
  }

  async function analyzeProduct() {
    if (!productQuery.trim()) {
      setErrorMessage(
        pick(
          "Scrie numele produsului sau scanează codul de bare. Exemplu: skyr natural.",
          "Enter the product name or scan its barcode. Example: plain skyr."
        )
      );
      return;
    }

    if (!user) {
      window.location.assign("/login");
      return;
    }

    setIsAnalyzing(true);
    setErrorMessage("");
    setUnknownProduct(null);
    localStorage.removeItem("cealeg_last_result");

    try {
      if (selectedSuggestion && !selectedFile) {
        const result = buildResultFromSuggestion(selectedSuggestion);

        localStorage.setItem("cealeg_last_result", JSON.stringify(result));
        await saveScanToBackend(result);
        window.location.assign(`/result?store=${storeParam}`);
        return;
      }

      if (!selectedFile) {
        setErrorMessage(
          pick(
            "Alege o potrivire din catalog sau încarcă o poză pentru citirea textului de pe ambalaj.",
            "Choose a catalog match or upload a photo to read the package text."
          )
        );
        return;
      }

      const formData = new FormData();
      formData.append("image", selectedFile);
      formData.append("store", storeParam);
      formData.append("product_query", productQuery.trim());
      formData.append("label_text", detectedLabelText);

      if (selectedSuggestion?.barcode) {
        formData.append("selected_barcode", String(selectedSuggestion.barcode));
      }

      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        body: formData,
      });

      const result = await readApiJson(response);

      if (!response.ok) {
        if (result.product_not_found) {
          setUnknownProduct(result);
          return;
        }

        throw new Error(getApiErrorMessage(result, pick, "Imaginea nu a putut fi analizată.", "The image could not be analyzed."));
      }

      localStorage.setItem("cealeg_last_result", JSON.stringify(result));

      await saveScanToBackend(result);

      window.location.assign(`/result?store=${storeParam}`);
    } catch (error) {
      console.error(error);
      setErrorMessage(
        error.message ||
          pick("Analiza nu este disponibilă acum. Încearcă din nou în câteva clipe.", "Analysis is unavailable right now. Try again in a few moments.")
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  function buildSubmitProductLink() {
    const params = new URLSearchParams();

    params.set("name", productQuery);
    params.set("store", storeName);

    return `/submit-product?${params.toString()}`;
  }

  if (!user) {
    return (
      <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#05080f] text-white">
        <div className="relative z-10 flex items-center gap-3 rounded-2xl border border-white/10 bg-black/35 px-5 py-4 shadow-2xl backdrop-blur">
          <Loader2 className="h-5 w-5 animate-spin text-cyan-200" />
          <p className="font-semibold text-gray-200" role="status">{pick("Se pregătește scanarea...", "Preparing scanner...")}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#05080f] text-white">
      <div className="relative z-10">
        <AppHeader actionHref="/barcode-scan" actionLabel={pick("Scanează codul", "Scan barcode")} />
      </div>
      <section className="ce-shell-md ce-page relative z-10 flex min-h-screen flex-col">
        <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/store"
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> {pick("Înapoi la alegerea magazinului", "Back to store selection")}
          </Link>

          <Link
            href="/history"
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-4 py-2 text-center text-sm font-semibold hover:bg-white/10"
          >
            <Clock3 size={16} />
            {pick("Istoric scanări", "Scan history")}
          </Link>
        </div>

        <div className="mb-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-stretch">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-cyan-300/35 bg-cyan-300/10 px-4 py-2 text-sm font-black text-cyan-100">
              <Search size={16} />
              {pick("Identificare prin cod sau nume", "Identify by barcode or name")}
            </p>
            <h1 className="mt-5 max-w-4xl text-3xl font-black leading-tight sm:text-4xl md:text-6xl">
              {pick("Găsește produsul corect fără să ghicești.", "Find the correct product without guessing.")}
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-gray-300 sm:text-lg sm:leading-8">
              {pick(
                "Identificarea sigură se face prin codul de bare sau denumirea de pe ambalaj. Fotografia este opțională și ajută la citirea locală a textului vizibil.",
                "Reliable identification uses the barcode or the name on the package. A photo is optional and helps read visible text locally."
              )}
            </p>

            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <a
                href="#product-lookup"
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-cyan-200 px-5 py-3 font-black text-slate-950 transition hover:-translate-y-0.5 hover:bg-white"
              >
                <Search size={18} />
                {pick("Caută produs după nume", "Search by product name")}
              </a>
              <Link
                href={`/barcode-scan?store=${storeParam}`}
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/12 bg-black/35 px-5 py-3 font-bold text-white transition hover:-translate-y-0.5 hover:bg-white/10"
              >
                <Barcode size={18} />
                {pick("Scanează codul de bare", "Scan barcode")}
              </Link>
            </div>
          </div>

          <InteractiveSurface className="rounded-3xl border border-cyan-300/20 bg-black/35 p-5 shadow-2xl backdrop-blur">
            <div className="flex items-start gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-cyan-300/12 text-cyan-100">
                <Info size={20} />
              </span>
              <div>
                <p className="text-sm font-black uppercase text-cyan-200">
                  {pick("AI vizual", "Visual AI")}
                </p>
                <h2 className="mt-1 text-2xl font-black">{pick("În dezvoltare", "In development")}</h2>
                <p className="mt-3 leading-7 text-gray-300">
                  {pick(
                    "Recunoașterea produsului doar din ambalaj nu este încă activă. Va fi separată clar de scanarea prin cod.",
                    "Product recognition from packaging alone is not active yet. It will be clearly separated from barcode scanning."
                  )}
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              {[
                [pick("Cod de bare", "Barcode"), pick("cea mai rapidă metodă", "the fastest method"), Barcode],
                [pick("Nume produs", "Product name"), pick("caută în catalogul online", "search the online catalog"), Search],
                [pick("Poză opțională", "Optional photo"), pick("citește local textul etichetei", "read label text locally"), Camera],
              ].map(([title, detail, Icon]) => (
                <div
                  key={title}
                  className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-3"
                >
                  <Icon className="h-5 w-5 text-cyan-200" />
                  <div>
                    <p className="font-black text-white">{title}</p>
                    <p className="text-sm text-gray-400">{detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </InteractiveSurface>
        </div>

        <InteractiveSurface
          id="product-lookup"
          className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-2xl backdrop-blur sm:rounded-3xl sm:p-6"
        >
          <div className="mb-6">
            <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-300/35 bg-cyan-300/10 px-4 py-2 text-sm font-black text-cyan-100">
              <Sparkles size={16} />
              {pick("Căutare asistată", "Assisted search")}
            </p>

            <h2 className="text-2xl font-black sm:text-3xl md:text-4xl">
              {pick("Scrie numele sau alege produsul corect din catalog.", "Enter a name or choose the correct catalog product.")}
            </h2>

            <div className="mt-5 rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">{pick("Magazin selectat", "Selected store")}</p>
              <p className="mt-1 text-xl font-black text-cyan-100">
                {storeName}
              </p>
            </div>

            <p className="mt-4 max-w-4xl leading-7 text-gray-300">
              {pick(
                "Căutarea folosește denumirea, codul de bare și catalogul online. Poza este folosită doar pentru a extrage textul vizibil de pe etichetă.",
                "Search uses the name, barcode and online catalog. The photo is only used to extract visible label text."
              )}
            </p>

            <div className="relative mt-5 rounded-2xl border border-white/10 bg-black/30 p-4">
              <label htmlFor="scan-product-query" className="text-sm font-semibold text-gray-300">
                {pick("Nume sau cod de pe ambalaj", "Name or code from the package")}
              </label>

              <input
                id="scan-product-query"
                value={productQuery}
                onChange={(e) => {
                  setProductQuery(e.target.value);
                  setSelectedSuggestion(null);
                  setUnknownProduct(null);
                  setErrorMessage("");
                  setSearchError("");
                }}
                placeholder={pick("Exemplu: iaurt natural, băutură fără zahăr", "Example: plain yogurt, sugar-free drink")}
                className="mt-3 w-full rounded-2xl border border-white/10 bg-[#0b0f14] px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-cyan-300"
              />

              <div className="mt-2 flex items-center justify-between">
                <p className="text-xs text-gray-500">
                  {pick("Alege potrivirea exactă. Scannerul este mai rapid când ai codul de bare.", "Choose the exact match. The scanner is faster when you have the barcode.")}
                </p>

                {(isSearching || isReadingLabel) && (
                  <p className="inline-flex items-center gap-1 text-xs text-cyan-200">
                    <Loader2 size={13} className="animate-spin" />
                    {isReadingLabel ? pick("Se citește eticheta...", "Reading label...") : pick("Se caută...", "Searching...")}
                  </p>
                )}
              </div>

              {detectedLabelText && (
                <div role="status" className="mt-3 rounded-2xl border border-sky-300/25 bg-sky-300/10 p-3 text-sm text-sky-100">
                  {pick("Text citit de pe ambalaj", "Text read from the package")}:{" "}
                  <span className="font-bold">{detectedLabelText}</span>
                </div>
              )}

              {searchError && (
                <div role="alert" className="mt-3 rounded-2xl border border-red-300/25 bg-red-300/10 p-3 text-sm text-red-200">
                  {searchError}
                </div>
              )}

              {selectedSuggestion && (
                <div className="mt-4 rounded-2xl border border-cyan-300/30 bg-cyan-300/10 p-3 text-sm text-cyan-100">
                  <div className="flex items-start gap-2">
                    <CheckCircle2 size={17} className="mt-0.5 shrink-0" />
                    <p>
                      {pick("Produs selectat", "Selected product")}:{" "}
                      <span className="font-bold">{selectedSuggestion.name}</span>.
                      {pick("Poți vedea analiza fără să încarci o poză.", "You can view the analysis without uploading a photo.")}
                    </p>
                  </div>
                </div>
              )}

              {suggestions.length > 0 && (
                <div className="mt-4 space-y-3 rounded-2xl border border-white/10 bg-[#0b0f14] p-3">
                  <p className="text-sm font-semibold text-gray-300">
                    {pick("Potriviri din catalog", "Catalog matches")}
                  </p>

                  {suggestions.map((product) => (
                    <button
                      key={product.barcode || product.id || product.name}
                      type="button"
                      onClick={() => selectSuggestion(product)}
                      className="grid w-full grid-cols-[auto_1fr] items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3 text-left transition hover:border-cyan-300/50 hover:bg-white/10 sm:grid-cols-[auto_1fr_auto]"
                    >
                      <ProductImage
                        src={getImageUrl(product.image)}
                        alt={product.name}
                        containerClassName="h-14 w-14 rounded-xl"
                        imageClassName="object-contain p-1"
                        fallbackClassName="text-2xl"
                      />

                      <div>
                        <h3 className="font-bold text-white">{product.name}</h3>
                        <p className="mt-1 text-xs text-gray-400">
                          {product.store} · {localizeCatalogLabel(product.category, locale)} ·{" "}
                          {product.priceText || pick("preț necunoscut", "unknown price")}
                        </p>
                      </div>

                      <div className="col-span-2 text-left sm:col-span-1 sm:text-right">
                        <span className="rounded-full bg-emerald-400 px-3 py-1 text-xs font-bold text-black">
                          {product.score === null ||
                          product.score === undefined ||
                          product.score === ""
                            ? pick("Date limitate", "Limited data")
                            : `${product.score}/10`}
                        </span>

                      </div>
                    </button>
                  ))}
                </div>
              )}

              {productQuery.trim().length >= 3 &&
                suggestions.length === 0 &&
                !isSearching &&
                !searchError &&
                !selectedSuggestion && (
                  <div className="mt-4 rounded-2xl border border-yellow-300/20 bg-yellow-300/10 p-3 text-sm text-yellow-300">
                    {pick(
                      "Nu avem încă o potrivire sigură. Scrie denumirea mai exact, scanează codul sau trimite produsul pentru verificare.",
                      "We do not have a reliable match yet. Enter a more precise name, scan the barcode or submit the product for review."
                    )}
                  </div>
                )}
            </div>
          </div>

          <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-white/20 bg-black/30 p-6 text-center transition hover:border-emerald-400/60 hover:bg-emerald-400/5 sm:rounded-3xl sm:p-10">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-300/12 text-cyan-100">
              <ImagePlus size={28} />
            </span>
            <span className="mt-4 text-lg font-semibold">
              {pick("Fotografie de referință, opțional", "Optional reference photo")}
            </span>
            <span className="mt-2 text-sm text-gray-400">
              {pick("Ajută la citirea textului vizibil, nu la recunoaștere vizuală completă.", "Helps read visible text; it does not provide full visual recognition.")}
            </span>

            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
              capture="environment"
              onChange={handleImageUpload}
              className="hidden"
            />
          </label>

          {imagePreview && (
            <div className="mt-8">
              <h2 className="mb-3 text-xl font-semibold">{pick("Imagine selectată", "Selected image")}</h2>

              <ProductImage
                src={imagePreview}
                alt={pick("Produs scanat", "Scanned product")}
                containerClassName="h-80 w-full rounded-2xl"
                imageClassName="object-cover"
                fallbackClassName="text-5xl"
              />

              {isReadingLabel && (
                <p className="mt-3 text-sm text-sky-200">
                  {pick("Citim local textul vizibil de pe ambalaj...", "Reading visible package text locally...")}
                </p>
              )}
            </div>
          )}

          <button
            onClick={analyzeProduct}
            disabled={isAnalyzing}
            className={`mt-6 flex w-full items-center justify-center gap-2 rounded-2xl px-6 py-4 text-center text-lg font-black transition ${
              isAnalyzing
                ? "cursor-not-allowed bg-white/10 text-gray-400"
                : "bg-white text-black hover:-translate-y-0.5 hover:bg-cyan-100"
            }`}
          >
            {isAnalyzing ? (
              <>
                <Loader2 size={19} className="animate-spin" />
                {pick("Căutăm produsul potrivit...", "Finding the right product...")}
              </>
            ) : selectedSuggestion ? (
              pick("Vezi analiza produsului selectat", "View selected product analysis")
            ) : selectedFile ? (
              pick("Caută produsul după textul din poză", "Search using text from the photo")
            ) : (
              pick("Continuă către analiză", "Continue to analysis")
            )}
          </button>

          {unknownProduct && (
            <div className="mt-6 rounded-3xl border border-yellow-300/30 bg-yellow-300/10 p-5">
              <h2 className="text-2xl font-bold text-yellow-300">
                {pick("Produsul nu a fost găsit", "Product not found")}
              </h2>

              <p className="mt-3 text-gray-300">
                {pick("Am căutat produsul", "We searched for")} {" "}
                <span className="font-bold text-white">
                  {unknownProduct.searchedText}
                </span>{" "}
                {pick("pentru magazinul", "in the store")} {" "}
                <span className="font-bold text-white">
                  {unknownProduct.store}
                </span>
                , dar nu l-am găsit.
              </p>

              {unknownProduct.matchScore !== undefined && (
                <p className="mt-2 text-sm text-gray-400">
                  {pick("Scor potrivire", "Match score")}: {unknownProduct.matchScore}
                </p>
              )}

              <p className="mt-3 text-sm text-gray-400">
                {pick(
                  "Nu afișăm automat un produs asemănător, fiindcă poate avea alte ingrediente sau valori nutriționale. Îl poți trimite pentru verificare și completarea catalogului.",
                  "We do not automatically show a similar product because it may have different ingredients or nutrition values. You can submit it for review and help complete the catalog."
                )}
              </p>

              <Link
                href={buildSubmitProductLink()}
                className="mt-5 inline-block rounded-2xl bg-yellow-300 px-6 py-3 font-semibold text-black hover:bg-yellow-200"
              >
                {pick("Contribuie cu acest produs", "Submit this product")}
              </Link>
            </div>
          )}

          {errorMessage && (
            <div role="alert" className="mt-6 rounded-2xl border border-red-400/30 bg-red-400/10 p-4 text-red-300">
              {errorMessage}
            </div>
          )}
        </InteractiveSurface>
      </section>
    </main>
  );
}

export default function ScanPage() {
  return (
    <Suspense fallback={null}>
      <ScanPageContent />
    </Suspense>
  );
}

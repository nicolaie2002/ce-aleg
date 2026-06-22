"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Clock3 } from "lucide-react";
import { API_URL } from "../config";
import { ProductImage } from "../components/ProductImage";
import { AppHeader } from "../components/AppHeader";

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
  const searchParams = useSearchParams();
  const storeParam = searchParams.get("store") || "any";
  const storeName = getStoreName(storeParam);

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

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Nu s-au putut încărca sugestiile.");
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
            error.message || "Catalogul extern nu răspunde acum. Încearcă din nou în câteva clipe."
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
  }, [productQuery, selectedSuggestion, storeParam, user?.id]);

  function selectSuggestion(product) {
    setSelectedSuggestion(product);
    setProductQuery(product.name);
    setSuggestions([]);
    setUnknownProduct(null);
    setErrorMessage("");
    setSearchError("");
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
    if (!selectedFile) {
      setErrorMessage("Te rog să încarci mai întâi o imagine.");
      return;
    }

    if (!productQuery.trim()) {
      setErrorMessage(
        "Scrie numele produsului detectat de pe ambalaj. Exemplu: Skyr natural, Monster Ultra White."
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

      const result = await response.json();

      if (!response.ok) {
        if (result.product_not_found) {
          setUnknownProduct(result);
          return;
        }

        throw new Error(result.error || "Imaginea nu a putut fi analizată.");
      }

      localStorage.setItem("cealeg_last_result", JSON.stringify(result));

      await saveScanToBackend(result);

      window.location.assign(`/result?store=${storeParam}`);
    } catch (error) {
      console.error(error);
      setErrorMessage(
        error.message ||
          "Analiza nu este disponibilă acum. Încearcă din nou în câteva clipe."
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
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300">Se încarcă scanarea...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel="Scanează codul" />
      <section className="ce-shell-md flex min-h-screen flex-col py-10">
        <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/store"
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> Înapoi la alegerea magazinului
          </Link>

          <Link
            href="/history"
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-4 py-2 text-center text-sm font-semibold hover:bg-white/10"
          >
            <Clock3 size={16} />
            Istoric scanări
          </Link>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl">
          <div className="mb-6">
            <p className="mb-3 inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-300">
              Scanare produs
            </p>

            <h1 className="text-4xl font-bold">
              Fă poză la produsul de pe raft.
            </h1>

            <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm text-gray-400">Magazin selectat</p>
              <p className="mt-1 text-xl font-bold text-emerald-300">
                {storeName}
              </p>
            </div>

            <p className="mt-4 text-gray-300">
              Încarcă o fotografie clară și scrie numele de pe ambalaj pentru a
              găsi produsul potrivit.
            </p>

            <div className="relative mt-5 rounded-2xl border border-white/10 bg-black/30 p-4">
              <label className="text-sm font-semibold text-gray-300">
                Numele produsului detectat
              </label>

              <input
                value={productQuery}
                onChange={(e) => {
                  setProductQuery(e.target.value);
                  setSelectedSuggestion(null);
                  setUnknownProduct(null);
                  setErrorMessage("");
                  setSearchError("");
                }}
                placeholder="Ex: monster alb, skyr, iaurt proteic"
                className="mt-3 w-full rounded-2xl border border-white/10 bg-[#0b0f14] px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />

              <div className="mt-2 flex items-center justify-between">
                <p className="text-xs text-gray-500">
                  Alege sugestia care corespunde produsului de pe raft.
                </p>

                {(isSearching || isReadingLabel) && (
                  <p className="text-xs text-emerald-300">Se caută...</p>
                )}
              </div>

              {detectedLabelText && (
                <div className="mt-3 rounded-2xl border border-sky-300/25 bg-sky-300/10 p-3 text-sm text-sky-100">
                  Text citit de pe ambalaj:{" "}
                  <span className="font-bold">{detectedLabelText}</span>
                </div>
              )}

              {searchError && (
                <div className="mt-3 rounded-2xl border border-red-300/25 bg-red-300/10 p-3 text-sm text-red-200">
                  {searchError}
                </div>
              )}

              {selectedSuggestion && (
                <div className="mt-4 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-300">
                  Produs selectat din catalogul extern:{" "}
                  <span className="font-bold">{selectedSuggestion.name}</span>
                </div>
              )}

              {suggestions.length > 0 && (
                <div className="mt-4 space-y-3 rounded-2xl border border-white/10 bg-[#0b0f14] p-3">
                  <p className="text-sm font-semibold text-gray-300">
                    Rezultate din catalogul extern
                  </p>

                  {suggestions.map((product) => (
                    <button
                      key={product.barcode || product.id || product.name}
                      type="button"
                      onClick={() => selectSuggestion(product)}
                      className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3 text-left transition hover:border-emerald-400/50 hover:bg-white/10"
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
                          {product.store} · {product.category} ·{" "}
                          {product.priceText || "preț necunoscut"}
                        </p>
                      </div>

                      <div className="text-right">
                        <span className="rounded-full bg-emerald-400 px-3 py-1 text-xs font-bold text-black">
                          {product.score === null ||
                          product.score === undefined ||
                          product.score === ""
                            ? "Date limitate"
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
                    Catalogul extern nu a găsit încă o potrivire sigură. Poți
                    continua căutarea cu numele exact de pe ambalaj sau poți
                    contribui produsul.
                  </div>
                )}
            </div>
          </div>

          <label className="flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed border-white/20 bg-black/30 p-10 text-center transition hover:border-emerald-400/60 hover:bg-emerald-400/5">
            <span className="text-5xl">📸</span>
            <span className="mt-4 text-lg font-semibold">
              Apasă ca să încarci poza
            </span>
            <span className="mt-2 text-sm text-gray-400">
              JPG, PNG, WEBP sau poză făcută direct cu telefonul
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
              <h2 className="mb-3 text-xl font-semibold">Imagine selectată</h2>

              <ProductImage
                src={imagePreview}
                alt="Produs scanat"
                containerClassName="h-80 w-full rounded-2xl"
                imageClassName="object-cover"
                fallbackClassName="text-5xl"
              />

              {isReadingLabel && (
                <p className="mt-3 text-sm text-sky-200">
                  Citim local textul vizibil de pe ambalaj...
                </p>
              )}

              <button
                onClick={analyzeProduct}
                disabled={isAnalyzing}
                className={`mt-6 block w-full rounded-2xl px-6 py-4 text-center text-lg font-semibold transition ${
                  isAnalyzing
                    ? "cursor-not-allowed bg-white/10 text-gray-400"
                    : "bg-emerald-400 text-black hover:bg-emerald-300"
                }`}
              >
                {isAnalyzing
                  ? "Căutăm produsul potrivit..."
                  : "Vezi analiza produsului"}
              </button>
            </div>
          )}

          {unknownProduct && (
            <div className="mt-6 rounded-3xl border border-yellow-300/30 bg-yellow-300/10 p-5">
              <h2 className="text-2xl font-bold text-yellow-300">
                Produsul nu a fost găsit
              </h2>

              <p className="mt-3 text-gray-300">
                Am căutat produsul{" "}
                <span className="font-bold text-white">
                  {unknownProduct.searchedText}
                </span>{" "}
                pentru magazinul{" "}
                <span className="font-bold text-white">
                  {unknownProduct.store}
                </span>
                , dar nu l-am găsit.
              </p>

              {unknownProduct.matchScore !== undefined && (
                <p className="mt-2 text-sm text-gray-400">
                  Scor potrivire: {unknownProduct.matchScore}
                </p>
              )}

              <p className="mt-3 text-sm text-gray-400">
                Nu afișăm automat un produs asemănător, fiindcă ar putea avea
                alte ingrediente sau valori nutriționale. Poți contribui
                produsul pentru verificare și completarea catalogului.
              </p>

              <Link
                href={buildSubmitProductLink()}
                className="mt-5 inline-block rounded-2xl bg-yellow-300 px-6 py-3 font-semibold text-black hover:bg-yellow-200"
              >
                Contribuie cu acest produs
              </Link>
            </div>
          )}

          {errorMessage && (
            <div className="mt-6 rounded-2xl border border-red-400/30 bg-red-400/10 p-4 text-red-300">
              {errorMessage}
            </div>
          )}
        </div>
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

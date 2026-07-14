"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Camera, CheckCircle2, Coins, FileText, ScanLine, Sparkles } from "lucide-react";
import { API_URL } from "../config";
import { ProductImage } from "../components/ProductImage";
import { AppHeader } from "../components/AppHeader";

const CATALOG_REWARD_COINS = 10;
const MAX_CONTRIBUTION_IMAGE_WIDTH = 1400;
const MAX_CONTRIBUTION_IMAGE_BYTES = 1_200_000;
const CONTRIBUTION_IMAGE_QUALITY = 0.82;

const SUBMISSION_STATUS = {
  pending: {
    label: "În verificare",
    detail: "Așteaptă verificarea adminului.",
    badge: "border-yellow-300/35 bg-yellow-300/10 text-yellow-100",
  },
  ai_approved: {
    label: "Gata de publicat",
    detail: "Verificarea automata arata bine. Adminul poate publica produsul.",
    badge: "border-cyan-300/35 bg-cyan-300/10 text-cyan-100",
  },
  approved: {
    label: "Aprobat",
    detail: "Produsul a intrat în catalog sau a confirmat un produs existent.",
    badge: "border-emerald-300/35 bg-emerald-300/10 text-emerald-100",
  },
  needs_review: {
    label: "Necesita revizie",
    detail: "Lipsesc informații sau pozele nu sunt destul de clare.",
    badge: "border-red-300/35 bg-red-300/10 text-red-100",
  },
};

function getSubmissionStatus(status) {
  return SUBMISSION_STATUS[status] || {
    label: status || "În verificare",
    detail: "Propunerea este în coada de verificare.",
    badge: "border-white/10 bg-white/[0.04] text-gray-200",
  };
}

function formatFileSize(bytes) {
  const size = Number(bytes || 0);

  if (!size) return "";
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function loadImageElement(file) {
  return new Promise((resolve, reject) => {
    const objectUrl = URL.createObjectURL(file);
    const image = new Image();

    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Imaginea nu a putut fi citita."));
    };
    image.src = objectUrl;
  });
}

async function optimizeContributionImage(file) {
  if (!file?.type?.startsWith("image/")) return file;

  const image = await loadImageElement(file);
  const scale = Math.min(
    1,
    MAX_CONTRIBUTION_IMAGE_WIDTH / Math.max(image.naturalWidth || image.width, 1)
  );

  if (scale === 1 && file.size <= MAX_CONTRIBUTION_IMAGE_BYTES) {
    return file;
  }

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round((image.naturalWidth || image.width) * scale));
  canvas.height = Math.max(1, Math.round((image.naturalHeight || image.height) * scale));
  canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);

  const blob = await new Promise((resolve) => {
    canvas.toBlob(resolve, "image/jpeg", CONTRIBUTION_IMAGE_QUALITY);
  });

  if (!blob) return file;

  if (blob.size >= file.size && file.size <= MAX_CONTRIBUTION_IMAGE_BYTES) {
    return file;
  }

  const baseName = (file.name || "produs").replace(/\.[^.]+$/, "");

  return new File([blob], `${baseName}.jpg`, {
    type: "image/jpeg",
    lastModified: Date.now(),
  });
}

function CaptureField({ id, title, description, file, icon: Icon, onChange, busy = false }) {
  return (
    <label
      htmlFor={id}
      className="block rounded-2xl border border-white/10 bg-black/25 p-4 transition hover:border-cyan-300/40 hover:bg-white/[0.055]"
    >
      <span className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-200 text-black">
          <Icon size={19} />
        </span>
        <span className="min-w-0">
          <span className="block font-black text-white">{title}</span>
          <span className="mt-1 block text-sm leading-6 text-gray-400">{description}</span>
          <span className={`mt-3 inline-flex max-w-full items-center gap-2 rounded-full border px-3 py-1 text-xs font-black ${
            file
              ? "border-emerald-300/35 bg-emerald-300/10 text-emerald-100"
              : "border-white/10 bg-white/[0.04] text-gray-300"
          }`}>
            {file ? <CheckCircle2 size={14} /> : <Camera size={14} />}
            <span className="truncate">
              {busy
                ? "Optimizez poza..."
                : file
                  ? `${file.name} ${formatFileSize(file.size)}`
                  : "Alege sau fa poza"}
            </span>
          </span>
        </span>
      </span>
      <input
        id={id}
        type="file"
        accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
        capture="environment"
        onChange={(event) => onChange(event.target.files?.[0] || null)}
        disabled={busy}
        className="sr-only"
      />
    </label>
  );
}

function SubmitProductPageContent() {
  const searchParams = useSearchParams();

  const suggestedName = searchParams.get("name") || "";
  const suggestedStore = searchParams.get("store") || "Lidl";
  const suggestedBarcode = searchParams.get("barcode") || "";
  const suggestedSource = searchParams.get("source") || "";
  const suggestedBarcodeConfirmed = searchParams.get("barcode_confirmed") === "1";

  const [user, setUser] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [imageNotice, setImageNotice] = useState("");
  const [imageBusyField, setImageBusyField] = useState("");
  const [lastSubmittedItem, setLastSubmittedItem] = useState(null);
  const [aiResult, setAiResult] = useState(null);

  const [form, setForm] = useState({
    productName: suggestedName,
    barcode: suggestedBarcode,
    brand: "",
    store: suggestedStore,
    category: "Băuturi",
    quantityValue: "",
    quantityUnit: "ml",
    price: "",
    calories: "",
    protein: "",
    sugar: "",
    fat: "",
    ingredients: "",
  });

  const [frontImage, setFrontImage] = useState(null);
  const [nutritionImage, setNutritionImage] = useState(null);

  useEffect(() => {
    queueMicrotask(() => {
      const savedUser = localStorage.getItem("cealeg_user");

      if (!savedUser) {
        window.location.assign("/login");
        return;
      }

      const parsedUser = JSON.parse(savedUser);
      setUser(parsedUser);
      loadSubmissions(parsedUser.id);
    });
  }, []);

  async function loadSubmissions(userId) {
    try {
      const response = await fetch(`${API_URL}/submissions/${userId}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-au putut încărca propunerile.");
      }

      setSubmissions(data);
    } catch (error) {
      setMessage(error.message);
    }
  }

  function updateField(field, value) {
    setForm({
      ...form,
      [field]: value,
    });
  }

  function buildQuantityText() {
    if (!form.quantityValue.trim()) {
      return "";
    }

    return `${form.quantityValue.trim()} ${form.quantityUnit}`;
  }

  async function handleContributionImageChange(field, file) {
    const setSelectedImage = field === "front" ? setFrontImage : setNutritionImage;

    if (!file) {
      setSelectedImage(null);
      setImageNotice("");
      return;
    }

    setImageBusyField(field);
    setImageNotice("Optimizez poza pentru upload...");

    try {
      const optimizedFile = await optimizeContributionImage(file);

      setSelectedImage(optimizedFile);
      setImageNotice(
        optimizedFile.size < file.size
          ? `Poza optimizată: ${formatFileSize(file.size)} -> ${formatFileSize(optimizedFile.size)}.`
          : "Poza adaugata."
      );
    } catch {
      setSelectedImage(file);
      setImageNotice("Nu am putut comprima poza, dar o folosesc asa cum este.");
    } finally {
      setImageBusyField("");
    }
  }

  async function handleAiExtract() {
    if (imageBusyField) {
      setMessage("Așteaptă câteva secunde până se optimizează poza.");
      return;
    }

    if (!frontImage && !nutritionImage && !form.productName.trim()) {
      setMessage("Încarcă cel puțin o poză sau scrie un nume aproximativ al produsului.");
      return;
    }

    setIsExtracting(true);
    setMessage("");
    setAiResult(null);

    try {
      const formData = new FormData();

      formData.append("product_hint", form.productName);

      if (frontImage) {
        formData.append("front_image", frontImage);
      }

      if (nutritionImage) {
        formData.append("nutrition_image", nutritionImage);
      }

      const response = await fetch(`${API_URL}/ai/extract-product-info`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Nu s-au putut extrage datele automat.");
      }

      const data = result.data;

      setForm((currentForm) => ({
        ...currentForm,
        productName: data.productName || currentForm.productName,
        brand: data.brand || currentForm.brand,
        category: data.category || currentForm.category,
        quantityValue: data.quantityValue || currentForm.quantityValue,
        quantityUnit: data.quantityUnit || currentForm.quantityUnit,
        calories: data.calories || currentForm.calories,
        protein: data.protein || currentForm.protein,
        sugar: data.sugar || currentForm.sugar,
        fat: data.fat || currentForm.fat,
        ingredients: data.ingredients || currentForm.ingredients,
      }));

      setAiResult(data);

      setMessage(
        `Câmpurile disponibile au fost completate automat. Verifică informațiile înainte de trimitere.`
      );
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!user) {
      window.location.assign("/login");
      return;
    }

    if (imageBusyField) {
      setMessage("Așteaptă câteva secunde până se optimizează poza.");
      return;
    }

    setIsSubmitting(true);
    setMessage("");

    try {
      const formData = new FormData();

      formData.append("user_id", user.id);
      formData.append("product_name", form.productName);
      formData.append("barcode", form.barcode);
      formData.append("brand", form.brand);
      formData.append("store", form.store);
      formData.append("category", form.category);
      formData.append("quantity", buildQuantityText());
      formData.append("price", form.price);
      formData.append("calories", form.calories);
      formData.append("protein", form.protein);
      formData.append("sugar", form.sugar);
      formData.append("fat", form.fat);
      formData.append("ingredients", form.ingredients);

      if (frontImage) {
        formData.append("front_image", frontImage);
      }

      if (nutritionImage) {
        formData.append("nutrition_image", nutritionImage);
      }

      const response = await fetch(`${API_URL}/submissions/add`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 409 && data.item) {
          setLastSubmittedItem(data.item);
          setMessage(data.message || "Propunerea există deja și este în verificare.");
          return;
        }

        throw new Error(data.message || data.error || "Nu s-a putut trimite produsul.");
      }

      setLastSubmittedItem(data.item || null);
      setMessage("Produsul a fost trimis la verificare. După aprobare primești scanare bonus și până la 10 CeCoins automat.");

      setForm({
        productName: "",
        barcode: "",
        brand: "",
        store: "Lidl",
        category: "Băuturi",
        quantityValue: "",
        quantityUnit: "ml",
        price: "",
        calories: "",
        protein: "",
        sugar: "",
        fat: "",
        ingredients: "",
      });

      setFrontImage(null);
      setNutritionImage(null);
      setAiResult(null);
      setImageNotice("");

      loadSubmissions(user.id);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function reviewWithAi(id) {
    try {
      const response = await fetch(`${API_URL}/submissions/ai-review/${id}`, {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut verifică produsul cu AI.");
      }

      let details = `${data.message} Grad de verificare: ${data.confidence}/100.`;

      if (data.problems && data.problems.length > 0) {
        details += ` Probleme: ${data.problems.join(" | ")}`;
      }

      if (data.warnings && data.warnings.length > 0) {
        details += ` Atenționări: ${data.warnings.join(" | ")}`;
      }

      setMessage(details);
      loadSubmissions(user.id);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function approveSubmission(id) {
    try {
      const response = await fetch(`${API_URL}/submissions/approve/${id}`, {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut publica produsul.");
      }

      setMessage(data.message || "Produsul a fost publicat în baza oficială.");
      loadSubmissions(user.id);
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function deleteSubmission(id) {
    try {
      const response = await fetch(`${API_URL}/submissions/item/${id}`, {
        method: "DELETE",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Nu s-a putut șterge propunerea.");
      }

      setSubmissions(submissions.filter((item) => item.id !== id));
      setMessage("Propunerea a fost ștearsă.");

      setTimeout(() => {
        setMessage("");
      }, 2500);
    } catch (error) {
      setMessage(error.message);
    }
  }

  function getImageUrl(path) {
    if (!path) return "";
    return `${API_URL}${path}`;
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300">Se încarcă pagina...</p>
      </main>
    );
  }

  const isAdmin = Boolean(user.isAdmin);

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/dashboard" actionLabel="Dashboard" />
      <section className="ce-shell ce-page">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> Înapoi la dashboard
          </Link>

          <Link
            href="/store"
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 text-center font-semibold hover:bg-white/10"
          >
            <ScanLine size={17} />
            Scanează produs
          </Link>
        </div>

        {message && (
          <div className="mb-6 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-300">
            {message}
          </div>
        )}

        {imageNotice && (
          <div className="mb-6 rounded-2xl border border-cyan-300/25 bg-cyan-300/10 p-4 text-sm font-bold text-cyan-100">
            {imageNotice}
          </div>
        )}

        {lastSubmittedItem && (
          <div className="mb-6 rounded-2xl border border-yellow-300/30 bg-yellow-300/10 p-4">
            <p className="text-sm font-black uppercase tracking-wide text-yellow-100">
              Trimis la verificare
            </p>
            <h2 className="mt-2 text-xl font-black text-white">
              {lastSubmittedItem.product_name}
            </h2>
            <p className="mt-2 text-sm leading-6 text-gray-300">
              Status: în verificare. După aprobare apare în catalog, primești scanare bonus și până la 10 CeCoins automat.
            </p>
            <Link
              href="/missions"
              className="mt-4 inline-flex rounded-xl bg-yellow-300 px-4 py-2.5 text-sm font-black text-black hover:bg-yellow-200"
            >
              Vezi misiunile
            </Link>
          </div>
        )}

        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl">
          <p className="mb-3 inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-300">
            Contribuie produs
          </p>

          <h1 className="text-4xl font-bold md:text-5xl">
            Adaugă un produs nou
          </h1>

          <p className="mt-4 max-w-3xl text-gray-300">
            Încarcă o fotografie a produsului și, dacă este disponibilă, o
            fotografie clară a etichetei nutriționale.
          </p>

          <div className="mt-5 rounded-2xl border border-cyan-300/25 bg-cyan-300/10 p-4 text-sm leading-6 text-cyan-50">
            Produsele acceptate primesc o scanare bonus și până la {CATALOG_REWARD_COINS} CeCoins automat după aprobare. Verificăm propunerile înainte să
            ajungă în catalog, ca recomandările să rămână curate.
          </div>

          {(suggestedName || suggestedStore || suggestedBarcode) && (
            <div className="mt-6 rounded-3xl border border-yellow-300/20 bg-yellow-300/10 p-5">
              <h2 className="text-xl font-bold text-yellow-300">
                {suggestedSource === "barcode_not_found"
                  ? "Produs negăsit în catalog"
                  : "Produs venit din scanare"}
              </h2>
              <p className="mt-2 text-sm text-gray-300">
                Formularul a fost completat cu datele disponibile din scanare.
                Verifică informațiile și completează restul câmpurilor.
              </p>

              {suggestedBarcode && (
                <div className={`mt-4 rounded-2xl border p-4 ${
                  suggestedBarcodeConfirmed
                    ? "border-cyan-300/25 bg-cyan-300/10"
                    : "border-yellow-300/25 bg-black/20"
                }`}>
                  <p className={`text-sm font-bold ${
                    suggestedBarcodeConfirmed ? "text-cyan-100" : "text-yellow-100"
                  }`}>
                    {suggestedBarcodeConfirmed
                      ? "Cod de bare confirmat în scanner"
                      : "Verifică încă o dată codul de bare"}
                  </p>
                  <code className="mt-2 block rounded-xl border border-white/10 bg-black/35 px-4 py-3 text-center font-mono text-xl font-black tracking-[0.16em] text-white">
                    {suggestedBarcode}
                  </code>
                  <p className="mt-3 text-sm leading-6 text-gray-300">
                    {suggestedBarcodeConfirmed
                      ? "Continuă cu pozele produsului și eticheta nutrițională."
                      : "Compară cifrele cu cele tipărite sub codul de pe ambalaj. Dacă nu sunt corecte, modifică valoarea în câmpul Cod de bare."}
                  </p>
                </div>
              )}
            </div>
          )}

          <div className="mt-6 rounded-3xl border border-yellow-300/20 bg-yellow-300/10 p-5">
            <p className="inline-flex items-center gap-2 text-sm font-black text-yellow-100">
              <Sparkles size={16} />
              Flow rapid pe telefon
            </p>
            <h2 className="mt-2 text-xl font-bold text-yellow-300">
              Poze, OCR, trimitere.
            </h2>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {[
                ["1", suggestedBarcode ? "Cod verificat" : "Cod opțional", suggestedBarcode || "Completează dacă îl ai"],
                ["2", "Față produs", frontImage ? "Poză adăugată" : "Fă o poză clară"],
                ["3", "Tabel nutrițional", nutritionImage ? "Poză adăugată" : "Fă poză etichetei"],
              ].map(([step, title, detail]) => (
                <div key={step} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-sm font-black text-black">
                    {step}
                  </span>
                  <p className="mt-3 font-black text-white">{title}</p>
                  <p className="mt-1 text-sm text-gray-400">{detail}</p>
                </div>
              ))}
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <CaptureField
                id="front-image-capture"
                title="Poză față produs"
                description="Ambalajul frontal ajută la nume, brand și imagine."
                file={frontImage}
                icon={Camera}
                busy={imageBusyField === "front"}
                onChange={(file) => handleContributionImageChange("front", file)}
              />
              <CaptureField
                id="nutrition-image-capture"
                title="Poză tabel nutrițional"
                description="Eticheta ajută la calorii, zahăr, proteină și grăsimi."
                file={nutritionImage}
                icon={FileText}
                busy={imageBusyField === "nutrition"}
                onChange={(file) => handleContributionImageChange("nutrition", file)}
              />
            </div>

            <button
              type="button"
              onClick={handleAiExtract}
              disabled={isExtracting || Boolean(imageBusyField)}
              className={`mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl px-5 py-3 font-semibold sm:w-auto ${
                isExtracting || imageBusyField
                  ? "cursor-not-allowed bg-white/10 text-gray-400"
                  : "border border-yellow-300/30 text-yellow-300 hover:bg-yellow-300/10"
              }`}
            >
              <Sparkles size={17} />
              {isExtracting ? "Se extrag datele..." : imageBusyField ? "Optimizez poza..." : "Extrage automat din poze"}
            </button>

            {aiResult && (
              <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-gray-300">
                <p className="font-semibold text-yellow-300">
                  Grad de completare: {aiResult.confidence}/100
                </p>

                {aiResult.notes?.length > 0 && (
                  <ul className="mt-2 list-inside list-disc">
                    {aiResult.notes.map((note, index) => (
                      <li key={index}>{note}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="mt-8 grid gap-5 md:grid-cols-2">
            <div>
              <label className="text-sm font-semibold text-gray-300">
                Nume produs *
              </label>
              <input
                value={form.productName}
                onChange={(e) => updateField("productName", e.target.value)}
                placeholder="Ex: Monster Energy Ultra White"
                className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
                required
              />
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Brand
              </label>
              <input
                value={form.brand}
                onChange={(e) => updateField("brand", e.target.value)}
                placeholder="Ex: Monster"
                className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Cod de bare
              </label>
              <input
                inputMode="numeric"
                value={form.barcode}
                onChange={(e) => updateField("barcode", e.target.value)}
                placeholder="Ex: 5941238013309"
                className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Magazin *
              </label>
              <select
                value={form.store}
                onChange={(e) => updateField("store", e.target.value)}
                className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0b0f14] px-4 py-3 text-white outline-none focus:border-emerald-400"
              >
                <option value="Lidl">Lidl</option>
                <option value="Kaufland">Kaufland</option>
                <option value="Carrefour">Carrefour</option>
                <option value="Mega Image">Mega Image</option>
                <option value="Profi">Profi</option>
                <option value="Penny">Penny</option>
                <option value="Market local">Market local</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Categorie
              </label>
              <select
                value={form.category}
                onChange={(e) => updateField("category", e.target.value)}
                className="mt-2 w-full rounded-2xl border border-white/10 bg-[#0b0f14] px-4 py-3 text-white outline-none focus:border-emerald-400"
              >
                <option value="Băuturi">Băuturi</option>
                <option value="Băuturi energizante">Băuturi energizante</option>
                <option value="Lactate">Lactate</option>
                <option value="Snacks">Snacks</option>
                <option value="Dulciuri">Dulciuri</option>
                <option value="Cereale">Cereale</option>
                <option value="Carne">Carne</option>
                <option value="Panificație">Panificație</option>
                <option value="Fructe și legume">Fructe și legume</option>
                <option value="Altele">Altele</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Cantitate / gramaj
              </label>

              <div className="mt-2 grid grid-cols-[1fr_auto] gap-3">
                <input
                  value={form.quantityValue}
                  onChange={(e) => updateField("quantityValue", e.target.value)}
                  placeholder="Ex: 500"
                  className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
                />

                <select
                  value={form.quantityUnit}
                  onChange={(e) => updateField("quantityUnit", e.target.value)}
                  className="rounded-2xl border border-white/10 bg-[#0b0f14] px-4 py-3 text-white outline-none focus:border-emerald-400"
                >
                  <option value="ml">ml</option>
                  <option value="L">L</option>
                  <option value="g">g</option>
                  <option value="kg">kg</option>
                  <option value="buc">buc</option>
                  <option value="pachet">pachet</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Preț estimativ
              </label>
              <input
                value={form.price}
                onChange={(e) => updateField("price", e.target.value)}
                placeholder="Ex: aprox. 6.49 lei"
                className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Calorii / 100 ml sau 100 g
              </label>
              <input
                type="number"
                value={form.calories}
                onChange={(e) => updateField("calories", e.target.value)}
                placeholder="Ex: 11"
                className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Proteină
              </label>
              <input
                type="number"
                value={form.protein}
                onChange={(e) => updateField("protein", e.target.value)}
                placeholder="Ex: 0"
                className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Zahăr
              </label>
              <input
                type="number"
                value={form.sugar}
                onChange={(e) => updateField("sugar", e.target.value)}
                placeholder="Ex: 0"
                className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <div>
              <label className="text-sm font-semibold text-gray-300">
                Grăsimi
              </label>
              <input
                type="number"
                value={form.fat}
                onChange={(e) => updateField("fat", e.target.value)}
                placeholder="Ex: 0"
                className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-sm font-semibold text-gray-300">
                Ingrediente / observații
              </label>
              <textarea
                value={form.ingredients}
                onChange={(e) => updateField("ingredients", e.target.value)}
                placeholder="Ex: fără zahăr, cu îndulcitori, conține cafeină..."
                className="mt-2 min-h-28 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
            </div>

            <button
              disabled={isSubmitting || Boolean(imageBusyField)}
              className={`md:col-span-2 rounded-2xl px-6 py-4 text-lg font-semibold transition ${
                isSubmitting || imageBusyField
                  ? "cursor-not-allowed bg-white/10 text-gray-400"
                  : "bg-emerald-400 text-black hover:bg-emerald-300"
              }`}
            >
              {isSubmitting
                ? "Se trimite produsul..."
                : imageBusyField
                  ? "Optimizez poza..."
                  : `Trimite la verificare - până la ${CATALOG_REWARD_COINS} CeCoins după aprobare`}
            </button>
          </form>
        </div>

        <div className="mt-8 rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl">
          <h2 className="text-3xl font-bold">Propunerile tale</h2>

          {submissions.length === 0 ? (
            <div className="mt-6 rounded-3xl border border-white/10 bg-black/30 p-8 text-center">
              <p className="text-5xl">📦</p>
              <h3 className="mt-4 text-2xl font-bold">
                Nu ai trimis încă produse
              </h3>
              <p className="mt-3 text-gray-400">
                Produsele trimise de tine vor apărea aici împreună cu starea verificării.
              </p>
            </div>
          ) : (
            <div className="mt-6 space-y-4">
              {submissions.map((item) => {
                const statusMeta = getSubmissionStatus(item.status);

                return (
                <div
                  key={item.id}
                  className="grid gap-4 rounded-3xl border border-white/10 bg-black/30 p-5 md:grid-cols-[auto_1fr_auto]"
                >
                  <ProductImage
                    src={getImageUrl(item.front_image)}
                    alt={item.product_name}
                    containerClassName="h-24 w-24 rounded-2xl"
                  />

                  <div>
                    <div className="flex flex-wrap gap-2">
                      <span className={`rounded-full border px-3 py-1 text-sm font-bold ${statusMeta.badge}`}>
                        {statusMeta.label}
                      </span>

                      <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                        {item.store}
                      </span>

                      {item.category && (
                        <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                          {item.category}
                        </span>
                      )}
                    </div>

                    <h3 className="mt-3 text-2xl font-bold">
                      {item.product_name}
                    </h3>

                    <p className="mt-2 text-sm leading-6 text-gray-400">
                      {statusMeta.detail}
                    </p>

                    <p className="mt-1 text-sm text-emerald-300">
                      {item.brand || "Brand necunoscut"} ·{" "}
                      {item.quantity || "cantitate necunoscută"} ·{" "}
                      {item.price || "preț necunoscut"}
                    </p>

                    <p className="mt-3 text-sm text-gray-300">
                      Kcal: {item.calories ?? "-"} · Proteină:{" "}
                      {item.protein ?? "-"}g · Zahăr: {item.sugar ?? "-"}g ·
                      Grăsimi: {item.fat ?? "-"}g
                    </p>

                    {item.ingredients && (
                      <p className="mt-3 text-sm leading-6 text-gray-400">
                        {item.ingredients}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    {isAdmin && (
                      <button
                        onClick={() => reviewWithAi(item.id)}
                        className="rounded-2xl border border-emerald-400/30 px-5 py-3 font-semibold text-emerald-300 hover:bg-emerald-400/10"
                      >
                        Verifică automat
                      </button>
                    )}

                    {isAdmin && item.status === "ai_approved" && (
                      <button
                        onClick={() => approveSubmission(item.id)}
                        className="rounded-2xl bg-emerald-400 px-5 py-3 font-semibold text-black hover:bg-emerald-300"
                      >
                        Publică produsul
                      </button>
                    )}

                    <button
                      onClick={() => deleteSubmission(item.id)}
                      className="rounded-2xl border border-red-400/30 px-5 py-3 font-semibold text-red-300 hover:bg-red-400/10"
                    >
                      Șterge
                    </button>
                  </div>
                </div>
                );
              })}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

export default function SubmitProductPage() {
  return (
    <Suspense fallback={null}>
      <SubmitProductPageContent />
    </Suspense>
  );
}

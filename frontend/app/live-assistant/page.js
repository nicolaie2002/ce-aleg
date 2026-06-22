"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BrowserMultiFormatReader } from "@zxing/browser";
import { BarcodeFormat, DecodeHintType } from "@zxing/library";
import Link from "next/link";
import {
  ArrowRight,
  Barcode,
  Camera,
  CameraIcon,
  Crown,
  Mic,
  MicOff,
  RefreshCw,
  ScanLine,
  Sparkles,
} from "lucide-react";
import { API_URL } from "../config";
import { AppHeader } from "../components/AppHeader";
import { useLocale } from "../components/LocaleProvider";
import { getActiveProfile, readProfilePreferences, saveProfilePreferences } from "../utils/profilePreferences";

function productToResult(product) {
  return {
    id: product.id,
    barcode: product.barcode,
    name: product.name,
    store: product.store,
    score: product.score,
    category: product.category,
    price: product.priceText || "preț necunoscut",
    priceSource: product.priceSource,
    priceStore: product.priceStore,
    priceDate: product.priceDate,
    calories: product.calories || 0,
    protein: product.protein || 0,
    sugar: product.sugar || 0,
    fat: product.fat || 0,
    image: product.image,
    verdict: product.reason || "Produs identificat din imagine.",
    shortAdvice: product.reason || "Produs identificat din imagine.",
  };
}

function createBarcodeReader() {
  const hints = new Map();

  hints.set(DecodeHintType.TRY_HARDER, true);
  hints.set(DecodeHintType.POSSIBLE_FORMATS, [
    BarcodeFormat.EAN_13,
    BarcodeFormat.EAN_8,
    BarcodeFormat.UPC_A,
    BarcodeFormat.UPC_E,
    BarcodeFormat.CODE_128,
    BarcodeFormat.CODE_39,
  ]);

  return new BrowserMultiFormatReader(hints, {
    delayBetweenScanAttempts: 120,
    delayBetweenScanSuccess: 500,
  });
}

function normalizeDetectedBarcode(value) {
  return String(value || "").replace(/\s+/g, "").trim();
}

function hasValidGs1Checksum(barcode) {
  const digits = barcode.split("").map(Number);
  const checkDigit = digits.pop();
  let weightedSum = 0;

  for (let index = digits.length - 1, position = 0; index >= 0; index -= 1, position += 1) {
    weightedSum += digits[index] * (position % 2 === 0 ? 3 : 1);
  }

  return (10 - (weightedSum % 10)) % 10 === checkDigit;
}

function isReliableScannedBarcode(barcode) {
  return (
    /^\d+$/.test(barcode) &&
    [8, 12, 13, 14].includes(barcode.length) &&
    hasValidGs1Checksum(barcode)
  );
}

function inferPreferenceCriteria(text) {
  const normalized = String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  const criteria = [];

  if (normalized.includes("ieftin") || normalized.includes("pret")) criteria.push("cheap");
  if (normalized.includes("proteina") || normalized.includes("protein")) criteria.push("protein");
  if (normalized.includes("calorii") || normalized.includes("slabit") || normalized.includes("dieta")) criteria.push("low_calorie");
  if (normalized.includes("zahar") || normalized.includes("dulce")) criteria.push("low_sugar");
  if (normalized.includes("post") || normalized.includes("vegan") || normalized.includes("vegetal")) criteria.push("vegan");
  if (normalized.includes("lactoza") || normalized.includes("lapte")) criteria.push("lactose_free");
  if (normalized.includes("natural") || normalized.includes("ingrediente") || normalized.includes("curat")) criteria.push("natural");
  if (normalized.includes("calitate") || normalized.includes("raport") || normalized.includes("valoare")) criteria.push("value");

  return criteria;
}

export default function LiveAssistantPage() {
  const { locale, pick } = useLocale();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const scannerControlsRef = useRef(null);
  const recognitionRef = useRef(null);
  const barcodeCandidateRef = useRef({ code: "", count: 0 });
  const detectedBarcodeRef = useRef(false);
  const analyzingRef = useRef(false);
  const [user, setUser] = useState(null);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [cloudVision, setCloudVision] = useState(false);
  const [cameraDevices, setCameraDevices] = useState([]);
  const [cameraIndex, setCameraIndex] = useState(0);
  const [transcript, setTranscript] = useState("");
  const [manualPreference, setManualPreference] = useState("");
  const [preferenceSummary, setPreferenceSummary] = useState("");
  const [message, setMessage] = useState(() => pick(
    "Pornește camera și încadrează codul de bare pentru o identificare rapidă.",
    "Start the camera and frame the barcode for fast identification."
  ));
  const [candidate, setCandidate] = useState(null);
  const [error, setError] = useState("");
  const [billingGate, setBillingGate] = useState(null);
  const [currentPlan, setCurrentPlan] = useState(null);
  const hasLiveAssistantAccess = currentPlan === "pro" || currentPlan === "family";
  const isCheckingBilling = currentPlan === null;

  const speak = useCallback((text) => {
    if (!text || typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = locale === "en" ? "en-US" : "ro-RO";
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  }, [locale]);

  useEffect(() => {
    queueMicrotask(() => {
      setVoiceSupported(Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));
      const savedUser = localStorage.getItem("cealeg_user");

      if (!savedUser) {
        window.location.assign("/login");
        return;
      }

      setUser(JSON.parse(savedUser));
      const activeProfile = getActiveProfile();
      const parsedPreferences = readProfilePreferences(activeProfile?.id);

      if (parsedPreferences) {
        const criteria = Array.isArray(parsedPreferences.criteria)
          ? parsedPreferences.criteria
          : [];
        const request = parsedPreferences.request || "";
        const summaryParts = [
          criteria.length ? criteria.join(", ") : "",
          request,
        ].filter(Boolean);
        setPreferenceSummary(summaryParts.join(" · "));
      }

      fetch(`${API_URL}/ai/status`)
        .then((response) => response.json())
        .then((data) => {
          const enabled = Boolean(data.cloudVision?.enabled);
          setCloudVision(enabled);

          if (!enabled) {
            setMessage(pick(
              "Camera folosește codul de bare pentru identificare precisă.",
              "The camera uses the barcode for precise identification."
            ));
          }
        })
        .catch(() => setCloudVision(false));

      fetch(`${API_URL}/billing/status`)
        .then(async (response) => {
          if (response.status === 401) {
            window.location.assign("/login?next=/live-assistant");
            return null;
          }

          return response.ok ? response.json() : null;
        })
        .then((data) => {
          const plan = data?.usage?.plan || "free";
          setCurrentPlan(plan);

          if (plan !== "pro" && plan !== "family") {
            setBillingGate({
              code: "paid_plan_required",
              plan,
            });
            setMessage(pick(
              "Asistentul live este inclus în Pro și Family. Pe Free poți folosi scanarea codului de bare.",
              "The live assistant is included in Pro and Family. On Free, you can use barcode scanning."
            ));
          }
        })
        .catch(() => {
          setCurrentPlan("free");
          setBillingGate({ code: "paid_plan_required", plan: "free" });
        });
    });
  }, [pick]);

  const stopCamera = useCallback(() => {
    scannerControlsRef.current?.stop?.();
    scannerControlsRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    detectedBarcodeRef.current = false;
    barcodeCandidateRef.current = { code: "", count: 0 };
    setIsCameraOn(false);
  }, []);

  async function startCamera(deviceId) {
    if (!hasLiveAssistantAccess) {
      setBillingGate({
        code: "paid_plan_required",
        plan: currentPlan || "free",
      });
      setMessage(pick(
        "Asistentul live este disponibil in Pro si Family. Scanarea codului de bare ramane disponibila pe Free.",
        "The live assistant is available in Pro and Family. Barcode scanning remains available on Free."
      ));
      return;
    }

    setError("");
    setCandidate(null);
    setBillingGate(null);
    setMessage(
      cloudVision
        ? pick(
            "Caut codul de bare și verific ambalajul. Ține produsul aproape, clar și bine luminat.",
            "Looking for the barcode and checking the package. Keep the product close, clear and well lit."
          )
        : pick(
            "Caut codul de bare. Ține produsul aproape, clar și bine luminat.",
            "Looking for the barcode. Keep the product close, sharp and well lit."
          )
    );
    scannerControlsRef.current?.stop?.();
    scannerControlsRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    detectedBarcodeRef.current = false;
    barcodeCandidateRef.current = { code: "", count: 0 };

    try {
      const reader = createBarcodeReader();
      scannerControlsRef.current = await reader.decodeFromVideoDevice(
        deviceId || undefined,
        videoRef.current,
        async (result) => {
          if (!result || detectedBarcodeRef.current) return;
          await handleDetectedBarcode(result.getText());
        }
      );

      streamRef.current = videoRef.current?.srcObject || null;

      setIsCameraOn(true);
      const devices = await navigator.mediaDevices.enumerateDevices();
      setCameraDevices(devices.filter((device) => device.kind === "videoinput"));
    } catch {
      setError(pick("Camera nu a putut fi pornită. Verifică permisiunea din browser.", "The camera could not start. Check your browser permission."));
    }
  }

  useEffect(
    () => () => {
      recognitionRef.current?.stop?.();
      stopCamera();
    },
    [stopCamera]
  );

  async function switchCamera() {
    if (!hasLiveAssistantAccess) {
      setBillingGate({
        code: "paid_plan_required",
        plan: currentPlan || "free",
      });
      return;
    }

    if (!cameraDevices.length) {
      await startCamera();
      return;
    }

    const nextIndex = (cameraIndex + 1) % cameraDevices.length;
    setCameraIndex(nextIndex);
    await startCamera(cameraDevices[nextIndex].deviceId);
  }

  async function handleDetectedBarcode(detectedCode) {
    const normalizedCode = normalizeDetectedBarcode(detectedCode);

    if (!isReliableScannedBarcode(normalizedCode)) {
      setMessage(pick(
        "Am vazut linii, dar codul nu e suficient de clar. Apropie produsul si tine camera nemiscata.",
        "I can see barcode lines, but the code is not clear enough. Move closer and keep the camera steady."
      ));
      return;
    }

    const previousCandidate = barcodeCandidateRef.current;
    const count = previousCandidate.code === normalizedCode
      ? previousCandidate.count + 1
      : 1;

    barcodeCandidateRef.current = { code: normalizedCode, count };
    setMessage(pick(
      `Cod detectat: ${normalizedCode}. Confirm produsul...`,
      `Code detected: ${normalizedCode}. Confirming product...`
    ));

    if (count < 3) return;

    detectedBarcodeRef.current = true;
    scannerControlsRef.current?.stop?.();
    scannerControlsRef.current = null;
    setMessage(pick(
      `Cod confirmat: ${normalizedCode}. Caut produsul...`,
      `Code confirmed: ${normalizedCode}. Looking up product...`
    ));
    await lookupBarcode(normalizedCode);
  }

  async function openProduct(product) {
    const result = productToResult(product);
    localStorage.setItem("cealeg_last_result", JSON.stringify(result));

    if (user) {
      await fetch(`${API_URL}/history/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id, ...result }),
      }).catch(() => null);
    }

    window.location.assign("/result?store=any");
  }

  async function lookupBarcode(barcode) {
    const response = await fetch(`${API_URL}/barcode/lookup/${barcode}`);
    const data = await response.json();

    if (data.code === "scan_limit_reached") {
      setBillingGate(data);
      setMessage(data.error || pick("Limita gratuita a fost atinsa.", "The free scan limit has been reached."));
      return;
    }

    if (response.ok && data.product) {
      await openProduct(data.product);
      return;
    }

    detectedBarcodeRef.current = false;
    barcodeCandidateRef.current = { code: "", count: 0 };
    setMessage(
      data.message ||
        pick(
          "Am citit un cod, dar nu am gasit produsul. Reincadrez camera si incerc din nou.",
          "I read a code, but could not find the product. I will keep looking."
        )
    );
  }

  const analyzeFrame = useCallback(async () => {
    if (!hasLiveAssistantAccess) {
      setBillingGate({
        code: "paid_plan_required",
        plan: currentPlan || "free",
      });
      setMessage(pick(
        "Asistentul live este disponibil in Pro si Family. Scanarea codului de bare ramane disponibila pe Free.",
        "The live assistant is available in Pro and Family. Barcode scanning remains available on Free."
      ));
      return;
    }

    if (!cloudVision || !videoRef.current || analyzingRef.current) return;

    const video = videoRef.current;
    if (!video.videoWidth || !video.videoHeight) return;

    analyzingRef.current = true;
    setIsAnalyzing(true);
    setError("");

    try {
      const canvas = canvasRef.current;
      const scale = Math.min(1, 960 / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.72));
      const form = new FormData();
      form.append("frame", blob, "camera.jpg");
      const response = await fetch(`${API_URL}/ai/identify-product-frame`, {
        method: "POST",
        body: form,
      });
      const data = await response.json();

      if (data.code === "scan_limit_reached") {
        setBillingGate(data);
        setMessage(data.error || pick("Limita gratuita a fost atinsa.", "The free scan limit has been reached."));
        return;
      }

      if (!response.ok) throw new Error(data.error || "Cadrul nu a putut fi analizat.");

      if (!data.identified) {
        setMessage(data.message || "Încă nu văd clar produsul. Apropie partea frontală a ambalajului.");
        return;
      }

      if (data.product) {
        const productMessage = `Am găsit ${data.product.name}. Poți deschide analiza completă.`;
        setCandidate({ ...data.candidate, product: data.product });
        setMessage(productMessage);
        speak(productMessage);
        return;
      }

      setCandidate(data.candidate);
      setMessage(data.candidate?.message || "Am recunoscut ambalajul. Arată și codul de bare pentru confirmare.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      analyzingRef.current = false;
      setIsAnalyzing(false);
    }
  }, [cloudVision, currentPlan, hasLiveAssistantAccess, pick, speak]);

  useEffect(() => {
    if (!isCameraOn || !cloudVision) return undefined;
    const interval = window.setInterval(analyzeFrame, 6000);
    return () => window.clearInterval(interval);
  }, [analyzeFrame, cloudVision, isCameraOn]);

  function savePreferenceText(text) {
    const cleanText = String(text || "").trim();

    if (!cleanText) {
      setError(pick(
      "Spune sau scrie ce vrei de la alternativă: mai ieftin, mai puțin zahăr, mai multă proteină.",
        "Say or write what you want from the alternative: cheaper, less sugar, more protein."
      ));
      return;
    }

    const activeProfile = getActiveProfile();
    const parsedPreferences = readProfilePreferences(activeProfile?.id) || {};
    const existingCriteria = Array.isArray(parsedPreferences.criteria)
      ? parsedPreferences.criteria
      : [];
    const nextCriteria = Array.from(
      new Set([...existingCriteria, ...inferPreferenceCriteria(cleanText)])
    );
    const previousRequest = String(parsedPreferences.request || "").trim();
    const nextRequest = previousRequest && !previousRequest.includes(cleanText)
      ? `${previousRequest}; ${cleanText}`
      : cleanText;

    saveProfilePreferences(activeProfile?.id, {
      profileId: activeProfile?.id || null,
      profileName: activeProfile?.name || "",
      criteria: nextCriteria,
      request: nextRequest.slice(0, 500),
    });
    setTranscript(cleanText);
    setManualPreference("");
    setPreferenceSummary(nextRequest.slice(0, 500));
    setError("");
    setMessage(pick(
      "Preferinta a fost salvata. O folosim cand iti alegem alternativele.",
      "Preference saved. We will use it when choosing alternatives."
    ));
  }

  async function requestMicrophoneAccess() {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(pick(
        "Browserul nu poate cere acces la microfon aici. Scrie preferinta in campul de mai jos.",
        "This browser cannot request microphone access here. Write the preference below."
      ));
    }

    const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioStream.getTracks().forEach((track) => track.stop());
  }

  async function listen() {
    const Recognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (isListening) {
      recognitionRef.current?.stop?.();
      setIsListening(false);
      return;
    }

    if (!Recognition) {
      setError(pick(
        "Dictarea nu este disponibila aici. Scrie preferinta si o salvam la fel.",
        "Voice dictation is not available here. Write the preference and we will save it the same way."
      ));
      return;
    }

    setError("");
    setMessage(pick(
      "Pregatesc microfonul...",
      "Preparing the microphone..."
    ));

    try {
      await requestMicrophoneAccess();
    } catch (permissionError) {
      setIsListening(false);
      setError(permissionError.message || pick(
        "Permite accesul la microfon din browser sau scrie preferinta manual.",
        "Allow microphone access in the browser or write the preference manually."
      ));
      return;
    }

    const recognition = new Recognition();
    recognitionRef.current = recognition;
    recognition.lang = locale === "en" ? "en-US" : "ro-RO";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onstart = () => {
      setIsListening(true);
      setMessage(pick(
        "Te ascult. Spune ce alternativa vrei.",
        "Listening. Say what alternative you want."
      ));
    };
    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };
    recognition.onerror = (event) => {
      setIsListening(false);
      recognitionRef.current = null;

      const permissionDenied = event.error === "not-allowed" || event.error === "service-not-allowed";
      const noAudio = event.error === "audio-capture";

      setError(
        permissionDenied
          ? pick(
              "Microfonul este blocat. Permite accesul din browser sau scrie preferinta manual.",
              "The microphone is blocked. Allow access in the browser or write the preference manually."
            )
          : noAudio
            ? pick(
                "Nu gasesc un microfon disponibil. Poti scrie preferinta manual.",
                "No microphone is available. You can write the preference manually."
              )
            : pick(
                "Nu am prins clar vocea. Incearca din nou sau scrie preferinta.",
                "I could not catch that clearly. Try again or write the preference."
              )
      );
    };
    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      savePreferenceText(text);
    };

    try {
      recognition.start();
    } catch {
      setIsListening(false);
      recognitionRef.current = null;
      setError(pick(
        "Dictarea este deja pornita sau nu a putut incepe. Incearca din nou.",
        "Voice dictation is already running or could not start. Try again."
      ));
    }
  }

  return (
    <main className="min-h-screen bg-[#080c10] text-white">
      <AppHeader actionHref={null} />
      <section className="ce-shell ce-page">
        <div className="flex flex-col gap-4 border-b border-white/10 pb-7 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-cyan-200">
              <Sparkles size={16} /> {pick("Asistent vizual Pro", "Visual assistant Pro")}
            </p>
            <h1 className="mt-3 max-w-3xl text-4xl font-black md:text-5xl">
              {pick("Asistentul de cumpărături cu cameră live.", "The shopping assistant with a live camera.")}
            </h1>
            <p className="mt-3 max-w-2xl text-gray-300">
              {pick("Camera identifică produsul prin codul de bare și pregătește analiza potrivită pentru magazinul și preferințele tale.", "The camera identifies the product through its barcode and prepares the right analysis for your store and preferences.")}
            </p>
          </div>
        </div>

        <div className="mt-7 grid gap-6 xl:grid-cols-[minmax(0,1fr)_430px] 2xl:grid-cols-[minmax(0,1fr)_460px]">
          <section className="overflow-hidden rounded-lg border border-white/10 bg-[#11171d]">
            <div className="relative aspect-[4/3] bg-black xl:aspect-[16/10]">
              <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
              {!isCameraOn && !hasLiveAssistantAccess && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-black/82 px-6 text-center text-gray-200">
                  <Crown className="text-yellow-200" size={38} />
                  <p className="max-w-sm font-bold">
                    {isCheckingBilling
                      ? pick("Verificam planul tau...", "Checking your plan...")
                      : pick(
                          "Asistentul live este inclus în Pro și Family.",
                          "The live assistant is included in Pro and Family."
                        )}
                  </p>
                  {!isCheckingBilling && (
                    <Link
                      href="/pricing"
                      className="mt-2 inline-flex rounded-lg bg-white px-4 py-2.5 font-black text-black hover:bg-cyan-100"
                    >
                      {pick("Vezi planurile", "View plans")}
                    </Link>
                  )}
                </div>
              )}
              {!isCameraOn && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-center text-gray-300">
                  <Camera className="text-cyan-200" size={36} />
                  <p>{pick("Pornește camera pentru a începe.", "Start the camera to begin.")}</p>
                </div>
              )}
              {isAnalyzing && (
                <div className="absolute inset-x-4 bottom-4 flex items-center gap-2 rounded-lg border border-cyan-300/30 bg-black/75 px-4 py-3 text-sm text-cyan-100">
                  <RefreshCw className="animate-spin" size={16} /> {pick("Analizez produsul din cadru...", "Analyzing the product in frame...")}
                </div>
              )}
            </div>
            <canvas ref={canvasRef} className="hidden" />
            <div className="flex flex-wrap gap-3 border-t border-white/10 p-4">
              <button onClick={() => (isCameraOn ? stopCamera() : startCamera())} className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-3 text-sm font-black text-black hover:bg-cyan-100">
                <CameraIcon size={17} /> {isCameraOn ? pick("Oprește camera", "Stop camera") : pick("Pornește camera", "Start camera")}
              </button>
              <button onClick={switchCamera} className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-bold hover:bg-white/10">
                <RefreshCw size={17} /> {pick("Schimbă camera", "Switch camera")}
              </button>
              {cloudVision && (
                <button onClick={analyzeFrame} className="inline-flex items-center gap-2 rounded-lg border border-cyan-300/40 px-4 py-3 text-sm font-bold text-cyan-100 hover:bg-cyan-300/10">
                  <ScanLine size={17} /> {pick("Analizează acum", "Analyze now")}
                </button>
              )}
            </div>
          </section>

          <aside className="space-y-4">
            <section className="rounded-lg border border-white/10 bg-[#11171d] p-5">
              <p className="text-xs font-bold uppercase text-cyan-200">{pick("Status scanare", "Scan status")}</p>
              <p className="mt-3 leading-7 text-gray-100">{message}</p>
            </section>

            <section className="rounded-lg border border-white/10 bg-[#11171d] p-5">
              <p className="text-sm font-bold">{pick("Preferinte pentru alternative", "Alternative preferences")}</p>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                {pick("Spune sau scrie ce contează: mai puțin zahăr, preț mai bun, proteină mai multă sau ingrediente mai simple.", "Say or write what matters: less sugar, better price, more protein or simpler ingredients.")}
              </p>
              <textarea
                value={manualPreference}
                onChange={(event) => setManualPreference(event.target.value)}
                placeholder={pick("Ex: vreau o variantă mai ieftină și fără mult zahăr", "Example: I want a cheaper option with less sugar")}
                className="mt-4 min-h-24 w-full rounded-lg border border-white/10 bg-black/30 p-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-cyan-300"
              />
              <div className={`mt-3 grid gap-2 ${voiceSupported ? "sm:grid-cols-2" : ""}`}>
                {voiceSupported && (
                  <button onClick={listen} className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-cyan-300/35 px-4 py-3 font-bold text-cyan-100 hover:bg-cyan-300/10">
                    {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                    {isListening ? pick("Te ascult...", "Listening...") : pick("Spune preferinta", "Speak preference")}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => savePreferenceText(manualPreference)}
                  className="inline-flex w-full items-center justify-center rounded-lg bg-white px-4 py-3 font-black text-black hover:bg-cyan-100"
                >
                  {pick("Salveaza preferinta", "Save preference")}
                </button>
              </div>
              {transcript && <p className="mt-3 text-sm text-gray-300">{transcript}</p>}
            </section>

            {!cloudVision && (
              <section className="rounded-lg border border-yellow-300/25 bg-yellow-300/10 p-5 text-sm leading-6 text-yellow-100">
                {pick(
                  "Pentru rezultate precise, camera confirmă produsul prin codul de bare, iar recomandările se bazează pe catalogul de produse.",
                  "For precise results, the camera confirms the product through the barcode and recommendations are based on the product catalog."
                )}
              </section>
            )}

            {preferenceSummary && (
              <section className="rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-5 text-sm leading-6 text-cyan-100">
                <p className="font-bold text-cyan-100">{pick("Preferințe active", "Active preferences")}</p>
                <p className="mt-2 text-cyan-50/90">{preferenceSummary}</p>
              </section>
            )}

            {billingGate && (
              <section className="rounded-lg border border-yellow-300/25 bg-yellow-300/10 p-5 text-sm leading-6 text-yellow-100">
                <p className="font-bold text-yellow-200">
                  {billingGate.code === "paid_plan_required"
                    ? pick("Asistent live inclus în Pro", "Live assistant included in Pro")
                    : pick("Limita gratuita a fost atinsa", "Free limit reached")}
                </p>
                <p className="mt-2">
                  {billingGate.code === "paid_plan_required"
                    ? pick(
                        "Foloseste scanarea codului de bare pe Free sau treci la Pro/Family pentru camera live.",
                        "Use barcode scanning on Free or switch to Pro/Family for the live camera."
                      )
                    : pick(
                    "Treci la Pro pentru scanări nelimitate.",
                        "Go Pro for unlimited scans."
                      )}
                </p>
                <Link
                  href="/pricing"
                  className="mt-4 inline-flex rounded-lg bg-white px-4 py-2.5 font-black text-black hover:bg-cyan-100"
                >
                  {pick("Vezi planurile", "View plans")}
                </Link>
              </section>
            )}

            {candidate && (
              <section className="rounded-lg border border-cyan-300/30 bg-cyan-300/10 p-5">
                <p className="text-xs font-bold uppercase text-cyan-100">{pick("Produs posibil", "Possible product")}</p>
                <h2 className="mt-2 text-xl font-black">{candidate.product?.name || candidate.name}</h2>
                {candidate.brand && <p className="mt-1 text-sm text-gray-300">{candidate.brand}</p>}
                {candidate.product && (
                  <button onClick={() => openProduct(candidate.product)} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 font-black text-black hover:bg-cyan-100">
                    {pick("Vezi analiza", "View analysis")} <ArrowRight size={17} />
                  </button>
                )}
                {!candidate.product && candidate.barcode && (
                  <button onClick={() => lookupBarcode(candidate.barcode)} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 font-black text-black hover:bg-cyan-100">
                    {pick("Confirmă după cod", "Confirm by barcode")} <Barcode size={17} />
                  </button>
                )}
              </section>
            )}
            {error && <p className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-200">{error}</p>}
          </aside>
        </div>
      </section>
    </main>
  );
}

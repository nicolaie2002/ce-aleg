"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, Search, SwitchCamera } from "lucide-react";
import { API_URL } from "../config";
import { ProductImage } from "../components/ProductImage";
import { AppHeader } from "../components/AppHeader";
import { useLocale } from "../components/LocaleProvider";
import { getActiveProfilePayload } from "../utils/profilePreferences";
import { trackEvent } from "../utils/analytics";
import { getApiErrorMessage, localizeApiMessage, readApiJson } from "../utils/apiResponse";

let barcodeReaderModulePromise = null;

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

async function loadBarcodeReaderModule() {
  if (!barcodeReaderModulePromise) {
    barcodeReaderModulePromise = Promise.all([
      import("@zxing/browser"),
      import("@zxing/library"),
    ]).then(([browserModule, libraryModule]) => ({
      BrowserMultiFormatReader: browserModule.BrowserMultiFormatReader,
      BarcodeFormat: libraryModule.BarcodeFormat,
      DecodeHintType: libraryModule.DecodeHintType,
    }));
  }

  return barcodeReaderModulePromise;
}

async function createBarcodeReader() {
  const { BrowserMultiFormatReader, BarcodeFormat, DecodeHintType } =
    await loadBarcodeReaderModule();
  const hints = new Map();

  hints.set(DecodeHintType.TRY_HARDER, true);
  hints.set(DecodeHintType.POSSIBLE_FORMATS, [
    BarcodeFormat.EAN_13,
    BarcodeFormat.EAN_8,
    BarcodeFormat.UPC_A,
    BarcodeFormat.ITF,
  ]);

  return new BrowserMultiFormatReader(hints, {
    delayBetweenScanAttempts:
      isLowPowerScannerDevice() || isCompactScannerViewport() ? 190 : 110,
    delayBetweenScanSuccess: 650,
  });
}

function normalizeDetectedBarcode(value) {
  return String(value || "").replace(/[^\d]/g, "").trim();
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
    !/^(\d)\1+$/.test(barcode) &&
    [8, 12, 13, 14].includes(barcode.length) &&
    hasValidGs1Checksum(barcode)
  );
}

const BARCODE_CONFIRMATION_WINDOW_MS = 2100;
const BARCODE_CANDIDATE_TTL_MS = 2800;
const BARCODE_DUPLICATE_LOOKUP_COOLDOWN_MS = 14000;

const STORE_OPTIONS = [
  "Lidl",
  "Kaufland",
  "Carrefour",
  "Mega Image",
  "Profi",
  "Penny",
  "Market local",
];

const SCAN_SOURCE_CONFIG = {
  native: { weight: 2.4, requiredCount: 2, requiredScore: 4.2 },
  zxing: { weight: 2.5, requiredCount: 2, requiredScore: 4.2 },
  rotated: { weight: 2.2, requiredCount: 2, requiredScore: 4.4 },
  ocr: { weight: 1.5, requiredCount: 2, requiredScore: 3 },
  manual: { weight: 5, requiredCount: 1, requiredScore: 1 },
};

function getScanSourceConfig(source) {
  return SCAN_SOURCE_CONFIG[source] || SCAN_SOURCE_CONFIG.zxing;
}

function createCroppedCanvas(sourceCanvas, widthRatio, heightRatio) {
  const cropWidth = Math.round(sourceCanvas.width * widthRatio);
  const cropHeight = Math.round(sourceCanvas.height * heightRatio);
  const canvas = document.createElement("canvas");
  canvas.width = cropWidth;
  canvas.height = cropHeight;
  canvas
    .getContext("2d")
    .drawImage(
      sourceCanvas,
      Math.round((sourceCanvas.width - cropWidth) / 2),
      Math.round((sourceCanvas.height - cropHeight) / 2),
      cropWidth,
      cropHeight,
      0,
      0,
      cropWidth,
      cropHeight
    );

  return canvas;
}

function createEnhancedCanvas(sourceCanvas, contrast = 1.7) {
  const canvas = document.createElement("canvas");
  canvas.width = sourceCanvas.width;
  canvas.height = sourceCanvas.height;
  const context = canvas.getContext("2d");
  context.filter = `grayscale(1) contrast(${contrast})`;
  context.drawImage(sourceCanvas, 0, 0);
  return canvas;
}

function buildScanAttempts(canvas) {
  const lighterScannerProfile = isLowPowerScannerDevice() || isCompactScannerViewport();
  const wideCenterCrop = createCroppedCanvas(canvas, 0.98, 0.64);
  const narrowCenterCrop = createCroppedCanvas(canvas, 0.96, 0.42);
  const verticalCenterCrop = createCroppedCanvas(canvas, 0.64, 0.96);

  if (lighterScannerProfile) {
    return [
      canvas,
      wideCenterCrop,
      narrowCenterCrop,
      verticalCenterCrop,
      createEnhancedCanvas(narrowCenterCrop, 2.1),
    ];
  }

  const centerCrop = createCroppedCanvas(canvas, 0.92, 0.74);

  return [
    canvas,
    createEnhancedCanvas(canvas, 1.55),
    wideCenterCrop,
    centerCrop,
    narrowCenterCrop,
    verticalCenterCrop,
    createEnhancedCanvas(wideCenterCrop),
    createEnhancedCanvas(narrowCenterCrop, 2.1),
    createEnhancedCanvas(verticalCenterCrop, 2),
  ];
}

function createOcrCanvas(video, angle = 0) {
  const radians = (angle * Math.PI) / 180;
  const swapsDimensions = angle === 90 || angle === 270;
  const maxWidth = isLowPowerScannerDevice() || isCompactScannerViewport() ? 960 : 1400;
  const scale = Math.min(1, maxWidth / video.videoWidth);
  const frameWidth = Math.round(video.videoWidth * scale);
  const frameHeight = Math.round(video.videoHeight * scale);
  const rotatedCanvas = document.createElement("canvas");
  rotatedCanvas.width = swapsDimensions ? frameHeight : frameWidth;
  rotatedCanvas.height = swapsDimensions ? frameWidth : frameHeight;
  const rotatedContext = rotatedCanvas.getContext("2d");
  rotatedContext.translate(rotatedCanvas.width / 2, rotatedCanvas.height / 2);
  rotatedContext.rotate(radians);
  rotatedContext.drawImage(
    video,
    -frameWidth / 2,
    -frameHeight / 2,
    frameWidth,
    frameHeight
  );

  const croppedCanvas = createCroppedCanvas(rotatedCanvas, 0.96, 0.7);
  const enhancedCanvas = createEnhancedCanvas(croppedCanvas, 2.2);
  const canvas = document.createElement("canvas");
  canvas.width = enhancedCanvas.width * 2;
  canvas.height = enhancedCanvas.height * 2;
  canvas
    .getContext("2d")
    .drawImage(enhancedCanvas, 0, 0, canvas.width, canvas.height);
  return canvas;
}

function extractValidOcrBarcodes(text) {
  const normalizedText = String(text || "").replace(/[Oo]/g, "0");
  const candidates = new Set(
    (normalizedText.match(/\d[\d\s-]{6,20}\d/g) || [])
      .map((value) => value.replace(/\D/g, ""))
      .filter((value) => [8, 12, 13, 14].includes(value.length))
  );

  return [...candidates].filter(isReliableScannedBarcode);
}

function isLowPowerScannerDevice() {
  if (typeof navigator === "undefined") return false;

  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;

  return (
    connection?.saveData ||
    (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) ||
    (navigator.deviceMemory && navigator.deviceMemory <= 4)
  );
}

function isCompactScannerViewport() {
  return typeof window !== "undefined" && window.innerWidth < 768;
}

function focusScannerPanel(element) {
  if (!element || typeof window === "undefined") return;

  window.requestAnimationFrame(() => {
    element.scrollIntoView({
      behavior: isCompactScannerViewport() ? "smooth" : "auto",
      block: "start",
    });
  });
}

function pulseScannerFeedback() {
  try {
    navigator?.vibrate?.(28);
  } catch {
    // Haptics are opțional and unsupported on many desktop browsers.
  }
}

export default function BarcodeScanPage() {
  const { pick } = useLocale();
  const videoRef = useRef(null);
  const confirmationPanelRef = useRef(null);
  const resultPanelRef = useRef(null);
  const missingProductPanelRef = useRef(null);
  const controlsRef = useRef(null);
  const streamRef = useRef(null);
  const scanLoopRef = useRef(null);
  const rotatedBarcodeTimerRef = useRef(null);
  const rotatedBarcodeRequestRef = useRef(false);
  const rotatedBarcodeReaderRef = useRef(null);
  const visionTimerRef = useRef(null);
  const visionRequestRef = useRef(false);
  const liveVisionEnabledRef = useRef(false);
  const ocrTimerRef = useRef(null);
  const ocrRequestRef = useRef(false);
  const ocrWorkerRef = useRef(null);
  const ocrPassRef = useRef(0);
  const ocrEnabledRef = useRef(true);
  const detectedRef = useRef(false);
  const barcodeCandidatesRef = useRef(new Map());
  const lookupInFlightRef = useRef(false);
  const lookupCooldownRef = useRef(new Map());
  const lastNativeScanAtRef = useRef(0);
  const lastFocusedPanelRef = useRef("");

  const [user, setUser] = useState(null);
  const [barcode, setBarcode] = useState("");
  const [message, setMessage] = useState("");
  const [foundProduct, setFoundProduct] = useState(null);
  const [productSource, setProductSource] = useState("");
  const [lookupIssue, setLookupIssue] = useState("");
  const [missingBarcodeCandidate, setMissingBarcodeCandidate] = useState(null);
  const [pendingBarcodeConfirmation, setPendingBarcodeConfirmation] = useState(null);
  const [billingGate, setBillingGate] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isLookingUp, setIsLookingUp] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [isAddingToCart, setIsAddingToCart] = useState(false);
  const [videoDevices, setVideoDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [scanStatus, setScanStatus] = useState("Camera este oprită.");
  /** @type {"auto" | "native" | "zxing"} */
  const scannerMode = "auto";
  const [liveVisionEnabled, setLiveVisionEnabled] = useState(false);
  const [, setIsVisionAnalyzing] = useState(false);
  const [visualCandidate, setVisualCandidate] = useState(null);
  const [torchSupported, setTorchSupported] = useState(false);
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [isOcrAnalyzing, setIsOcrAnalyzing] = useState(false);
  const [isPriceFormOpen, setIsPriceFormOpen] = useState(false);
  const [observedPrice, setObservedPrice] = useState("");
  const [observedStore, setObservedStore] = useState("");
  const [selectedStore, setSelectedStore] = useState("Kaufland");
  const [isSavingPrice, setIsSavingPrice] = useState(false);

  useEffect(() => {
    liveVisionEnabledRef.current = liveVisionEnabled;

    if (!liveVisionEnabled && visionTimerRef.current) {
      clearTimeout(visionTimerRef.current);
      visionTimerRef.current = null;
    }
  }, [liveVisionEnabled]);

  useEffect(() => {
    window.localStorage?.setItem("cealeg_scan_store", selectedStore);
    setObservedStore((currentStore) => currentStore || selectedStore);
  }, [selectedStore]);

  useEffect(() => {
    const hasMissingProductPrompt =
      !foundProduct &&
      barcode &&
      message &&
      (missingBarcodeCandidate ||
        [
          "openfoodfacts_unavailable",
          "external_product_not_found",
          "external_catalog_unavailable",
        ].includes(lookupIssue));

    let panelKey = "";
    let panelElement = null;

    if (pendingBarcodeConfirmation?.barcode) {
      panelKey = `confirm:${pendingBarcodeConfirmation.barcode}`;
      panelElement = confirmationPanelRef.current;
    } else if (foundProduct) {
      panelKey = `found:${foundProduct.barcode || foundProduct.id || foundProduct.name}`;
      panelElement = resultPanelRef.current;
    } else if (hasMissingProductPrompt) {
      panelKey = `missing:${missingBarcodeCandidate?.barcode || barcode}:${lookupIssue || "local"}`;
      panelElement = missingProductPanelRef.current;
    }

    if (!panelKey || !panelElement || lastFocusedPanelRef.current === panelKey) {
      return;
    }

    lastFocusedPanelRef.current = panelKey;
    focusScannerPanel(panelElement);
    pulseScannerFeedback();
  }, [
    barcode,
    foundProduct,
    lookupIssue,
    message,
    missingBarcodeCandidate,
    pendingBarcodeConfirmation,
  ]);

  const loadScannerCapabilities = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/ai/status`);
      const data = await readApiJson(response);
      const enabled = Boolean(response.ok && data.cloudVision?.enabled);

      liveVisionEnabledRef.current = enabled;
      setLiveVisionEnabled(enabled);
    } catch {
      liveVisionEnabledRef.current = false;
      setLiveVisionEnabled(false);
    }
  }, []);

  const loadVideoDevices = useCallback(async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        setMessage(pick("Browserul nu permite listarea camerelor.", "Your browser cannot list available cameras."));
        return;
      }

      const devices = await navigator.mediaDevices.enumerateDevices();
      const cameras = devices.filter((device) => device.kind === "videoinput");

      setVideoDevices(cameras);

      if (cameras.length > 0) {
        const backCamera =
          cameras.find((camera) =>
            camera.label.toLowerCase().includes("back")
          ) ||
          cameras.find((camera) =>
            camera.label.toLowerCase().includes("rear")
          ) ||
          cameras.find((camera) =>
            camera.label.toLowerCase().includes("environment")
          );

        setSelectedDeviceId(backCamera?.deviceId || cameras[0].deviceId);
      }
    } catch {
      setMessage(pick("Nu am putut lista camerele disponibile.", "Available cameras could not be listed."));
    }
  }, [pick]);

  useEffect(() => {
    queueMicrotask(() => {
      const savedUser = localStorage.getItem("cealeg_user");
      const savedStore = localStorage.getItem("cealeg_scan_store");

      if (!savedUser) {
        window.location.assign("/login");
        return;
      }

      if (savedStore && STORE_OPTIONS.includes(savedStore)) {
        setSelectedStore(savedStore);
        setObservedStore(savedStore);
      } else {
        setObservedStore("Kaufland");
      }

      setUser(JSON.parse(savedUser));
      loadVideoDevices();
      loadScannerCapabilities();
    });

    return () => {
      stopScanner();
      ocrWorkerRef.current?.terminate?.();
      ocrWorkerRef.current = null;
    };
  }, [loadScannerCapabilities, loadVideoDevices]);

  async function requestCameraPermissionAndReloadDevices() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: false,
      });

      stream.getTracks().forEach((track) => track.stop());

      await loadVideoDevices();

      setMessage(pick("Permisiunea pentru cameră este activă.", "Camera permission is active."));
    } catch {
      setMessage(pick("Nu ai permis accesul la cameră sau browserul a blocat camera.", "Camera access was denied or blocked by your browser."));
    }
  }

  function getFastCameraConstraints(deviceId = selectedDeviceId) {
    const lighterCameraProfile = isLowPowerScannerDevice() || isCompactScannerViewport();
    const idealWidth = lighterCameraProfile ? 1280 : 1920;
    const idealHeight = lighterCameraProfile ? 720 : 1080;
    const idealFrameRate = lighterCameraProfile ? 24 : 30;

    if (deviceId) {
      return {
        video: {
          deviceId: { exact: deviceId },
          width: { ideal: idealWidth },
          height: { ideal: idealHeight },
          frameRate: { ideal: idealFrameRate },
        },
        audio: false,
      };
    }

    return {
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: idealWidth },
        height: { ideal: idealHeight },
        frameRate: { ideal: idealFrameRate },
      },
      audio: false,
    };
  }

  async function configureCameraTrack(stream) {
    const track = stream?.getVideoTracks?.()[0];

    if (!track) return;

    const capabilities = track.getCapabilities?.() || {};
    setTorchSupported(Boolean(capabilities.torch));

    if (capabilities.focusMode?.includes("continuous")) {
      try {
        await track.applyConstraints({
          advanced: [{ focusMode: "continuous" }],
        });
      } catch {
        // Unele browsere raportează capabilitatea, dar nu acceptă setarea explicită.
      }
    }
  }

  async function toggleTorch() {
    const track = streamRef.current?.getVideoTracks?.()[0];

    if (!track) return;

    const nextValue = !torchEnabled;

    try {
      await track.applyConstraints({ advanced: [{ torch: nextValue }] });
      setTorchEnabled(nextValue);
    } catch {
      setMessage(pick("Lanterna nu poate fi controlată de acest browser.", "This browser cannot control the flashlight."));
    }
  }

  async function startScanner(deviceId = selectedDeviceId) {
    setMessage("");
    setFoundProduct(null);
    setProductSource("");
    setLookupIssue("");
    setMissingBarcodeCandidate(null);
    setPendingBarcodeConfirmation(null);
    setVisualCandidate(null);
    setBarcode("");
    setScanStatus("Pornesc camera...");
    detectedRef.current = false;
    lastNativeScanAtRef.current = 0;
    barcodeCandidatesRef.current.clear();
    rotatedBarcodeReaderRef.current = null;
    trackEvent("scan_started", {
      mode: scannerMode,
      source: "barcode_scan",
    });

    stopScanner();

    if (scannerMode === "native" || scannerMode === "auto") {
      const nativeStarted = await startNativeBarcodeDetector(deviceId);

      if (nativeStarted) {
        return;
      }
    }

    await startZxingScanner(deviceId);
  }

  async function startNativeBarcodeDetector(deviceId) {
    const BarcodeDetector = window.BarcodeDetector;

    if (!BarcodeDetector) {
      if (scannerMode === "native") {
        setMessage(pick("Browserul tău nu suportă scannerul nativ. Folosește modul ZXing.", "Your browser does not support the native scanner. Use ZXing mode."));
      }

      return false;
    }

    try {
      setIsScanning(true);
      setScanStatus("Pregătesc camera...");

      const stream = await navigator.mediaDevices.getUserMedia(
        getFastCameraConstraints(deviceId)
      );

      streamRef.current = stream;
      await configureCameraTrack(stream);

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      const preferredFormats = ["ean_13", "ean_8", "upc_a", "itf"];
      const supportedFormats =
        typeof BarcodeDetector.getSupportedFormats === "function"
          ? await BarcodeDetector.getSupportedFormats()
          : preferredFormats;
      const detectorFormats = preferredFormats.filter((format) =>
        supportedFormats.includes(format)
      );
      const detector = new BarcodeDetector({
        formats: detectorFormats.length ? detectorFormats : preferredFormats.slice(0, 3),
      });

      setScanStatus("Camera este pregătită. Încadrează codul de bare.");
      startRotatedBarcodeLoop();
      startBarcodeOcrLoop();
      startLiveVisionLoop();
      const nativeScanInterval =
        isLowPowerScannerDevice() || isCompactScannerViewport() ? 210 : 130;

      async function scanFrame() {
        if (!videoRef.current || detectedRef.current) {
          return;
        }

        try {
          const now = performance.now();

          if (now - lastNativeScanAtRef.current >= nativeScanInterval) {
            lastNativeScanAtRef.current = now;
            const codes = await detector.detect(videoRef.current);

            for (const code of codes || []) {
              const detectedCode = code?.rawValue;

              if (detectedCode && !detectedRef.current) {
                const detectionState = await handleDetectedBarcode(detectedCode, "native");

                if (detectionState === "confirmed") return;
              }
            }
          }
        } catch {
        }

        scanLoopRef.current = requestAnimationFrame(scanFrame);
      }

      scanLoopRef.current = requestAnimationFrame(scanFrame);

      return true;
    } catch {

      if (scannerMode === "native") {
        setMessage(pick("Nu am putut porni scannerul nativ. Încearcă modul ZXing.", "The native scanner could not start. Try ZXing mode."));
      }

      setIsScanning(false);
      return false;
    }
  }

  async function startZxingScanner(deviceId) {
    setMessage("");
      setScanStatus(pick("Pregătesc camera...", "Preparing camera..."));

    try {
      setIsScanning(true);

      const codeReader = await createBarcodeReader();
      const deviceIdToUse = deviceId || undefined;

      controlsRef.current = await codeReader.decodeFromVideoDevice(
        deviceIdToUse,
        videoRef.current,
        async (result) => {
          if (result && !detectedRef.current) {
            const detectedCode = result.getText();

            await handleDetectedBarcode(detectedCode, "zxing");
          } else if (!detectedRef.current) {
            setScanStatus(
              "Caut codul de bare. Apropie produsul, păstrează imaginea clară și evită reflexiile."
            );
          }
        }
      );

      streamRef.current = videoRef.current?.srcObject || null;
      await configureCameraTrack(streamRef.current);
      setScanStatus("Camera este pregătită. Încadrează codul de bare.");
      startRotatedBarcodeLoop();
      startBarcodeOcrLoop();
      startLiveVisionLoop();
    } catch {
      setMessage(pick("Nu am putut porni camera. Verifică permisiunea sau încearcă altă cameră.", "The camera could not start. Check permission or try another camera."));
      setScanStatus(pick("Camera nu a pornit.", "The camera did not start."));
      setIsScanning(false);
    }
  }

  function stopScanner() {
    if (rotatedBarcodeTimerRef.current) {
      clearTimeout(rotatedBarcodeTimerRef.current);
      rotatedBarcodeTimerRef.current = null;
    }

    if (visionTimerRef.current) {
      clearTimeout(visionTimerRef.current);
      visionTimerRef.current = null;
    }

    if (ocrTimerRef.current) {
      clearTimeout(ocrTimerRef.current);
      ocrTimerRef.current = null;
    }

    if (scanLoopRef.current) {
      cancelAnimationFrame(scanLoopRef.current);
      scanLoopRef.current = null;
    }

    if (controlsRef.current) {
      controlsRef.current.stop();
      controlsRef.current = null;
    }

    rotatedBarcodeReaderRef.current = null;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject;
      const tracks = stream.getTracks();

      tracks.forEach((track) => track.stop());

      videoRef.current.srcObject = null;
    }

    setIsScanning(false);
    setIsVisionAnalyzing(false);
    setTorchSupported(false);
    setTorchEnabled(false);
    setIsOcrAnalyzing(false);
  }

  function startRotatedBarcodeLoop() {
    if (rotatedBarcodeTimerRef.current) return;

    rotatedBarcodeTimerRef.current = setTimeout(async function scanNextFrame() {
      rotatedBarcodeTimerRef.current = null;

      if (detectedRef.current || !videoRef.current?.srcObject) {
        return;
      }

      await scanRotatedBarcodeFrame();

      if (!detectedRef.current && videoRef.current?.srcObject) {
        rotatedBarcodeTimerRef.current = setTimeout(
          scanNextFrame,
          isLowPowerScannerDevice() || isCompactScannerViewport() ? 720 : 420
        );
      }
    }, 250);
  }

  function pruneBarcodeCandidates(now = Date.now()) {
    for (const [candidateCode, candidate] of barcodeCandidatesRef.current) {
      if (now - candidate.lastSeen > BARCODE_CANDIDATE_TTL_MS) {
        barcodeCandidatesRef.current.delete(candidateCode);
      }
    }
  }

  function isBarcodeLookupCoolingDown(code, now = Date.now()) {
    const cooldownUntil = lookupCooldownRef.current.get(code);

    if (!cooldownUntil) return false;

    if (cooldownUntil <= now) {
      lookupCooldownRef.current.delete(code);
      return false;
    }

    return true;
  }

  async function handleDetectedBarcode(detectedCode, source = "zxing") {
    if (!detectedCode || detectedRef.current) return "ignored";

    const normalizedCode = normalizeDetectedBarcode(detectedCode);

    if (!isReliableScannedBarcode(normalizedCode)) {
      setScanStatus("Apropie produsul și ține-l nemișcat pentru o clipă.");
      return "invalid";
    }

    const now = Date.now();
    pruneBarcodeCandidates(now);

    if (isBarcodeLookupCoolingDown(normalizedCode, now)) {
      setScanStatus("Cod verificat recent. Caută un unghi mai clar dacă produsul nu apare.");
      return "cooldown";
    }

    const previousCandidate = barcodeCandidatesRef.current.get(normalizedCode);
    const sourceConfig = getScanSourceConfig(source);

    if (previousCandidate && now - previousCandidate.lastSeen < 120) {
      return "pending";
    }

    const sameCandidateIsFresh =
      previousCandidate &&
      now - previousCandidate.lastSeen < BARCODE_CONFIRMATION_WINDOW_MS;
    const sourceHits = sameCandidateIsFresh
      ? { ...(previousCandidate?.sourceHits || {}) }
      : {};
    sourceHits[source] = (sourceHits[source] || 0) + 1;
    const count =
      sameCandidateIsFresh
        ? previousCandidate.count + 1
        : 1;
    const score =
      sameCandidateIsFresh
        ? previousCandidate.score + sourceConfig.weight
        : sourceConfig.weight;
    const firstSeen =
      sameCandidateIsFresh
        ? previousCandidate.firstSeen
        : now;
    const requiredScore = sourceConfig.requiredScore;
    const requiredCount = sourceConfig.requiredCount;

    barcodeCandidatesRef.current.set(normalizedCode, {
      count,
      score,
      firstSeen,
      lastSeen: now,
      sourceHits,
    });

    setBarcode(normalizedCode);

    if (score < requiredScore || count < requiredCount) {
      setScanStatus("Am găsit codul. Confirm produsul...");
      return "pending";
    }

    detectedRef.current = true;
    setPendingBarcodeConfirmation({
      barcode: normalizedCode,
      source,
      detectedAt: now,
    });
    setScanStatus("Cod citit. Verifică cifrele înainte să caut produsul.");
    stopScanner();
    return "confirmed";
  }

  async function scanRotatedBarcodeFrame() {
    const video = videoRef.current;

    if (
      rotatedBarcodeRequestRef.current ||
      detectedRef.current ||
      !video ||
      video.readyState < 2 ||
      !video.videoWidth ||
      !video.videoHeight
    ) {
      return;
    }

    rotatedBarcodeRequestRef.current = true;

    try {
      let reader = rotatedBarcodeReaderRef.current;

      if (!reader) {
        reader = await createBarcodeReader();
        rotatedBarcodeReaderRef.current = reader;
      }

      const lighterScannerProfile = isLowPowerScannerDevice() || isCompactScannerViewport();
      const scanAngles = lighterScannerProfile ? [0, 90, 270] : [0, 90, 180, 270];

      for (const angle of scanAngles) {
        if (detectedRef.current) return;

        const radians = (angle * Math.PI) / 180;
        const swapsDimensions = angle === 90 || angle === 270;
        const maxWidth = lighterScannerProfile ? 900 : 1080;
        const scale = Math.min(1, maxWidth / video.videoWidth);
        const frameWidth = Math.round(video.videoWidth * scale);
        const frameHeight = Math.round(video.videoHeight * scale);
        const canvas = document.createElement("canvas");
        canvas.width = swapsDimensions ? frameHeight : frameWidth;
        canvas.height = swapsDimensions ? frameWidth : frameHeight;

        const context = canvas.getContext("2d");
        context.translate(canvas.width / 2, canvas.height / 2);
        context.rotate(radians);
        context.drawImage(
          video,
          -frameWidth / 2,
          -frameHeight / 2,
          frameWidth,
          frameHeight
        );

        const attempts = buildScanAttempts(canvas);

        for (const attemptCanvas of attempts) {
          try {
            const result = reader.decodeFromCanvas(attemptCanvas);
            const detectionState = await handleDetectedBarcode(result.getText(), "rotated");

            if (detectionState !== "invalid") {
              return;
            }
          } catch {
            // Cadrul curent nu conține un cod lizibil în această zonă.
          }
        }
      }
    } finally {
      rotatedBarcodeRequestRef.current = false;
    }
  }

  async function getOcrWorker() {
    if (!ocrWorkerRef.current) {
      const { createWorker } = await import("tesseract.js");
      ocrWorkerRef.current = await createWorker("eng");
    }

    return ocrWorkerRef.current;
  }

  function startBarcodeOcrLoop() {
    if (!ocrEnabledRef.current || ocrTimerRef.current) return;

    ocrTimerRef.current = setTimeout(async function analyzeNextOcrFrame() {
      ocrTimerRef.current = null;

      if (
        detectedRef.current ||
        !ocrEnabledRef.current ||
        !videoRef.current?.srcObject
      ) {
        return;
      }

      await analyzeBarcodeNumbersWithOcr();

      if (
        !detectedRef.current &&
        ocrEnabledRef.current &&
        videoRef.current?.srcObject
      ) {
        ocrTimerRef.current = setTimeout(
          analyzeNextOcrFrame,
          isLowPowerScannerDevice() || isCompactScannerViewport() ? 5400 : 3200
        );
      }
    }, isLowPowerScannerDevice() || isCompactScannerViewport() ? 9200 : 5200);
  }

  async function analyzeBarcodeNumbersWithOcr() {
    const video = videoRef.current;

    if (
      ocrRequestRef.current ||
      !video ||
      video.readyState < 2 ||
      !video.videoWidth ||
      !video.videoHeight
    ) {
      return;
    }

    ocrRequestRef.current = true;
    setIsOcrAnalyzing(true);

    try {
      const worker = await getOcrWorker();
      const angles =
        isLowPowerScannerDevice() || isCompactScannerViewport()
          ? [0, 90, 270]
          : [0, 90, 270, 180];
      const angle = angles[ocrPassRef.current % angles.length];
      ocrPassRef.current += 1;
      await worker.setParameters({
        tessedit_char_whitelist: "0123456789 -",
      });
      const result = await worker.recognize(createOcrCanvas(video, angle));
      const candidates = extractValidOcrBarcodes(result.data.text);

      for (const candidate of candidates) {
        const detectionState = await handleDetectedBarcode(candidate, "ocr");

        if (detectionState !== "invalid") {
          setScanStatus("Verific codul identificat...");
          return;
        }
      }

      if (ocrPassRef.current % 3 === 0) {
        await identifyLabelTextLocally(worker, video);
      }
    } catch {
      setScanStatus(
        "Caut codul... apropie lent produsul și evită reflexiile puternice."
      );
    } finally {
      ocrRequestRef.current = false;
      setIsOcrAnalyzing(false);
    }
  }

  async function identifyLabelTextLocally(worker, video) {
    await worker.setParameters({ tessedit_char_whitelist: "" });
    const result = await worker.recognize(createOcrCanvas(video));
    const labelText = result.data.text.replace(/\s+/g, " ").trim();

    if (labelText.length < 5) return;

    const response = await fetch(
      `${API_URL}/products/search-label?q=${encodeURIComponent(labelText.slice(0, 180))}`
    );
    const products = await readApiJson(response);
    const bestMatch = Array.isArray(products) ? products[0] : null;

    if (!response.ok || !bestMatch || bestMatch.matchScore < 55) return;

    setVisualCandidate({
      name: bestMatch.name,
      barcode: bestMatch.barcode,
      confidence: Math.min(99, Math.round(bestMatch.matchScore)),
      message: "Text identificat local de pe ambalaj. Confirmă produsul.",
      product: bestMatch,
    });
    setScanStatus(`Etichetă posibilă: ${bestMatch.name}`);
  }

  function startLiveVisionLoop() {
    if (!liveVisionEnabledRef.current || visionTimerRef.current) return;

    visionTimerRef.current = setTimeout(async function analyzeNextFrame() {
      visionTimerRef.current = null;

      if (
        detectedRef.current ||
        !liveVisionEnabledRef.current ||
        !videoRef.current?.srcObject
      ) {
        return;
      }

      await identifyCurrentFrame();

      if (
        !detectedRef.current &&
        liveVisionEnabledRef.current &&
        videoRef.current?.srcObject
      ) {
        visionTimerRef.current = setTimeout(analyzeNextFrame, 4000);
      }
    }, 3000);
  }

  async function identifyCurrentFrame() {
    const video = videoRef.current;

    if (
      visionRequestRef.current ||
      detectedRef.current ||
      !video ||
      video.readyState < 2 ||
      !video.videoWidth ||
      !video.videoHeight
    ) {
      return;
    }

    visionRequestRef.current = true;
    setIsVisionAnalyzing(true);

    try {
      const maxWidth = 640;
      const scale = Math.min(1, maxWidth / video.videoWidth);
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);

      const context = canvas.getContext("2d");
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      const blob = await new Promise((resolve) => {
        canvas.toBlob(resolve, "image/jpeg", 0.72);
      });

      if (!blob) return;

      const formData = new FormData();
      formData.append("frame", blob, "camera-frame.jpg");

      const response = await fetch(`${API_URL}/ai/identify-product-frame`, {
        method: "POST",
        body: formData,
      });
      const data = await readApiJson(response);

      if (response.status === 503 && data.code === "vision_not_configured") {
        liveVisionEnabledRef.current = false;
        setLiveVisionEnabled(false);
        setScanStatus(
          "Camera rămâne activă. Continuă scanarea codului de bare."
        );
        return;
      }

      if (response.status === 503 && data.code === "vision_unavailable") {
        liveVisionEnabledRef.current = false;
        setLiveVisionEnabled(false);
        setScanStatus(
          "Camera rămâne activă. Continuă scanarea codului de bare."
        );
        return;
      }

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Cadrul nu a putut fi analizat.", "The camera frame could not be analyzed."));
      }

      if (!data.identified) {
        setScanStatus(
          (data.message && localizeApiMessage(data.message, pick, data.code)) ||
            pick("Caut produsul... arată partea frontală sau codul de bare.", "Looking for the product... show the front or barcode.")
        );
        return;
      }

      setVisualCandidate(data.candidate);

      if (data.product) {
        detectedRef.current = true;
        setFoundProduct(data.product);
        setProductSource(data.source || "local");
        setMessage("");
        stopScanner();
        return;
      }

      if (data.candidate?.barcode) {
        setBarcode(data.candidate.barcode);
      }

      setScanStatus(
        data.candidate?.message ||
          "Produs probabil identificat. Arată codul de bare pentru date exacte."
      );
    } catch (error) {
      setScanStatus(
        "Camera rămâne activă. Continuă scanarea codului de bare."
      );
    } finally {
      visionRequestRef.current = false;
      setIsVisionAnalyzing(false);
    }
  }

  async function restartScanner() {
    stopScanner();

    setTimeout(() => {
      startScanner();
    }, 250);
  }

  async function lookupBarcode(code, sourceOverride = "") {
    const lookupCode = normalizeDetectedBarcode(code);
    const lookupSource = sourceOverride || (detectedRef.current ? "scanner" : "manual");
    let shouldRestartAfterMiss = false;

    if (!lookupCode) {
      setMessage(pick("Introdu sau scanează un cod de bare.", "Enter or scan a barcode."));
      return;
    }

    if (!isReliableScannedBarcode(lookupCode)) {
      setBarcode(lookupCode);
      setMessage(pick("Codul pare citit greșit. Verifică cifrele sau scanează din nou.", "The code may have been read incorrectly. Check the digits or scan again."));
      setScanStatus(pick("Cod nevalid. Apropie camera și ține produsul nemișcat.", "Invalid code. Move the camera closer and hold the product still."));
      return;
    }

    if (lookupInFlightRef.current) {
      setScanStatus("Caut deja produsul. Așteaptă câteva secunde...");
      return;
    }

    const now = Date.now();
    const coolingDown = isBarcodeLookupCoolingDown(lookupCode, now);

    if (coolingDown && detectedRef.current) {
      setScanStatus("Cod verificat recent. Încearcă un unghi mai clar dacă produsul nu apare.");
      return;
    }

    lookupInFlightRef.current = true;
    lookupCooldownRef.current.set(
      lookupCode,
      now + BARCODE_DUPLICATE_LOOKUP_COOLDOWN_MS
    );
    setBarcode(lookupCode);
    setIsLookingUp(true);
    setMessage("");
    setFoundProduct(null);
    setLookupIssue("");
    setMissingBarcodeCandidate(null);
    setPendingBarcodeConfirmation(null);
    setBillingGate(null);
    trackEvent("barcode_lookup", {
      barcode: lookupCode,
      source: lookupSource,
      length: lookupCode.length,
      store: selectedStore,
    });

    try {
      const response = await fetch(`${API_URL}/barcode/lookup/${lookupCode}`);
      const data = await readApiJson(response);

      if (!response.ok) {
        setLookupIssue(data.code || (response.status === 404 ? "external_product_not_found" : ""));

        if (data.code === "scan_limit_reached") {
          setBillingGate(data);
          setLookupIssue("scan_limit_reached");
        } else if (response.status === 404 || data.code === "external_product_not_found") {
          shouldRestartAfterMiss = false;
          setLookupIssue(data.code || "external_product_not_found");
          trackEvent("product_missing", {
            barcode: lookupCode,
            source: lookupSource,
            reason: data.code || response.status,
            store: selectedStore,
          });
          setMissingBarcodeCandidate({
            barcode: lookupCode,
            source: lookupSource,
            confirmed: lookupSource === "scanner_confirmed",
          });
          detectedRef.current = false;
          barcodeCandidatesRef.current.clear();
          stopScanner();
          setScanStatus("Produs negăsit. Confirmă codul citit înainte să îl adaugi.");
        }
        throw new Error(getApiErrorMessage(data, pick, "Produsul nu a fost găsit.", "The product was not found."));
      }

      setFoundProduct(data.product);
      setProductSource(data.source);
      setMissingBarcodeCandidate(null);
      setMessage("");
      trackEvent("product_found", {
        barcode: lookupCode,
        source: data.source || "barcode",
        category: data.product?.category || "",
        score: data.product?.score ?? "",
      });
    } catch (error) {
      setMessage(error.message);
    } finally {
      lookupInFlightRef.current = false;
      setIsLookingUp(false);

      if (shouldRestartAfterMiss) {
        setScanStatus("Produs negăsit. Continui scanarea cu un cod mai clar...");
        setTimeout(() => startScanner(), 500);
      }
    }
  }

  function switchCamera() {
    if (videoDevices.length < 2) {
      setMessage(pick("Nu am găsit o altă cameră disponibilă.", "No other camera is available."));
      return;
    }

    const currentIndex = videoDevices.findIndex(
      (device) => device.deviceId === selectedDeviceId
    );
    const nextDevice = videoDevices[(currentIndex + 1) % videoDevices.length];

    setSelectedDeviceId(nextDevice.deviceId);

    if (isScanning) {
      stopScanner();
      setTimeout(() => startScanner(nextDevice.deviceId), 250);
    }
  }

  async function confirmVisualCandidate() {
    if (!visualCandidate?.product) return;

    detectedRef.current = true;
    stopScanner();
    await goToResult(visualCandidate.product);
  }

  async function importProduct(product) {
    setIsImporting(true);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/barcode/import`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(product),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        setLookupIssue(data.code || "not_found");
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut salva produsul în catalog.", "The product could not be saved to the catalog."));
      }

      setFoundProduct(data.product);
      setProductSource("local");
      setMessage(
        data.message
          ? localizeApiMessage(data.message, pick, data.code)
          : pick("Produs salvat în catalog.", "Product saved to the catalog.")
      );
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsImporting(false);
    }
  }

  async function saveScanToHistory(product) {
    if (!user) return;

    await fetch(`${API_URL}/history/add`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user.id,
        name: product.name,
        store: product.store || "Cod de bare",
        category: product.category,
        score: product.score,
        price: product.priceText || "preț necunoscut",
        image: product.image,
        verdict: product.reason,
        shortAdvice: product.reason,
      }),
    });
  }

  async function addToCart(product) {
    if (isAddingToCart) return;

    if (!user) {
      window.location.assign("/login");
      return;
    }

    setIsAddingToCart(true);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/cart/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          name: product.name,
          store: product.store || "Cod de bare",
          score: product.score,
          price: product.priceText || "preț necunoscut",
          image: product.image,
          reason: product.reason || "Produs identificat după codul de bare.",
          quantity: 1,
          ...getActiveProfilePayload(),
        }),
      });

      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Nu s-a putut adăuga produsul în coș.", "The product could not be added to the cart."));
      }

      setMessage(pick(`Produs adăugat în coș: ${product.name}`, `Added to cart: ${product.name}`));
      window.dispatchEvent(new CustomEvent("cealeg:cart-updated"));
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsAddingToCart(false);
    }
  }

  function rescanMissingBarcode() {
    setMissingBarcodeCandidate(null);
    setPendingBarcodeConfirmation(null);
    setLookupIssue("");
    setMessage("");
    setBarcode("");
    setFoundProduct(null);
    detectedRef.current = false;
    restartScanner();
  }

  function editMissingBarcode() {
    setMissingBarcodeCandidate(null);
    setPendingBarcodeConfirmation(null);
    detectedRef.current = false;
    setLookupIssue("");
    setMessage(pick("Corectează codul din câmpul manual, apoi apasă Caută produsul.", "Correct the code in the manual field, then select Search product."));
    setScanStatus(pick("Verifică cifrele tipărite sub codul de bare.", "Check the digits printed under the barcode."));
  }

  function rejectPendingBarcode() {
    setPendingBarcodeConfirmation(null);
    setBarcode("");
    setMessage("");
    setLookupIssue("");
    detectedRef.current = false;
    barcodeCandidatesRef.current.clear();
    restartScanner();
  }

  function editPendingBarcode() {
    setPendingBarcodeConfirmation(null);
    setMessage(pick("Corectează codul din câmpul manual, apoi apasă Caută produsul.", "Correct the code in the manual field, then select Search product."));
    setScanStatus(pick("Verifică cifrele tipărite sub codul de bare.", "Check the digits printed under the barcode."));
    detectedRef.current = false;
  }

  async function confirmPendingBarcode() {
    const confirmedCode = pendingBarcodeConfirmation?.barcode || barcode;

    if (!confirmedCode || isLookingUp) return;

    detectedRef.current = true;
    setPendingBarcodeConfirmation(null);
    setScanStatus("Cod confirmat de tine. Caut produsul...");
    await lookupBarcode(confirmedCode, "scanner_confirmed");
  }

  async function saveObservedPrice() {
    if (!user || !foundProduct?.barcode) return;

    setIsSavingPrice(true);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/prices/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: user.id,
          barcode: foundProduct.barcode,
          store: observedStore.trim(),
          price: observedPrice,
        }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(getApiErrorMessage(data, pick, "Prețul nu a putut fi salvat.", "The price could not be saved."));
      }

      setFoundProduct((currentProduct) => ({
        ...currentProduct,
        ...data.price,
      }));
      setObservedPrice("");
      setIsPriceFormOpen(false);
      setMessage(
        data.message
          ? localizeApiMessage(data.message, pick, data.code)
          : pick("Prețul a fost salvat.", "The price was saved.")
      );
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsSavingPrice(false);
    }
  }

  async function goToResult(product) {
    const result = {
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
      verdict: product.reason || "Produs identificat după codul de bare.",
      shortAdvice: product.reason || "Produs identificat după codul de bare.",
    };

    localStorage.setItem("cealeg_last_result", JSON.stringify(result));

    await saveScanToHistory(result);

    window.location.assign("/result?store=any");
  }

  function buildSubmitProductLink(confirmed = false) {
    const params = new URLSearchParams();
    const contributionBarcode = missingBarcodeCandidate?.barcode || barcode;

    params.set("name", "");
    params.set("store", selectedStore || "Market local");
    params.set("barcode", contributionBarcode);
    params.set("source", "barcode_not_found");

    if (confirmed) {
      params.set("barcode_confirmed", "1");
    }

    return `/submit-product?${params.toString()}`;
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300">Se încarcă scannerul...</p>
      </main>
    );
  }

  const hasMissingProductPrompt =
    !foundProduct &&
    barcode &&
    message &&
    (missingBarcodeCandidate ||
      [
        "openfoodfacts_unavailable",
        "external_product_not_found",
        "external_catalog_unavailable",
      ].includes(lookupIssue));
  const mobileStatusTitle = pendingBarcodeConfirmation
    ? "Confirmă codul"
    : foundProduct
      ? "Produs găsit"
      : hasMissingProductPrompt
        ? "Produs nou"
        : isScanning
          ? "Camera pornita"
          : "Scanner pregătit";
  const mobileStatusDetail =
    pendingBarcodeConfirmation?.barcode ||
    foundProduct?.name ||
    missingBarcodeCandidate?.barcode ||
    scanStatus;

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/dashboard" actionLabel="Dashboard" />
      <section className="ce-shell-md ce-page pb-24 sm:pb-12">
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
            <Search size={17} />
            Scanare după nume
          </Link>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-4 shadow-2xl sm:rounded-3xl sm:p-6">
          <p className="mb-3 inline-flex rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm font-bold text-emerald-300">
            Scanare cod de bare
          </p>

          <h1 className="text-3xl font-black leading-tight sm:text-4xl md:text-5xl">
            Scanează codul. Confirmă produsul.
          </h1>

          <p className="mt-4 max-w-2xl text-sm leading-6 text-gray-300 sm:text-base sm:leading-7">
            Ține codul în chenar câteva clipe. Dacă produsul lipsește, verifici codul citit
            și îl poți trimite rapid la verificare pentru CeCoins.
          </p>

          <div className="mt-5 rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.06] p-4">
            <label className="text-sm font-black text-cyan-100">
              Magazin curent
            </label>
            <div className="mt-3 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <select
                value={selectedStore}
                onChange={(event) => setSelectedStore(event.target.value)}
                className="min-h-12 rounded-2xl border border-white/10 bg-[#0b0f14] px-4 text-white outline-none focus:border-cyan-300"
              >
                {STORE_OPTIONS.map((storeName) => (
                  <option key={storeName} value={storeName}>
                    {storeName}
                  </option>
                ))}
              </select>
              <p className="text-sm leading-6 text-gray-300">
                Folosim magazinul pentru prețuri și produse lipsă.
              </p>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4">
            <label className="text-sm font-semibold text-gray-300">
              Camera folosită
            </label>

            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <select
                value={selectedDeviceId}
                onChange={(e) => setSelectedDeviceId(e.target.value)}
                className="flex-1 rounded-2xl border border-white/10 bg-[#0b0f14] px-4 py-3 text-white outline-none focus:border-emerald-400"
              >
                {videoDevices.length === 0 ? (
                  <option value="">Nicio cameră listată încă</option>
                ) : (
                  videoDevices.map((device, index) => (
                    <option key={device.deviceId} value={device.deviceId}>
                      {device.label || `Camera ${index + 1}`}
                    </option>
                  ))
                )}
              </select>

              <button
                onClick={requestCameraPermissionAndReloadDevices}
                className="rounded-2xl border border-white/10 px-5 py-3 font-semibold hover:bg-white/10"
              >
                Actualizează camerele
              </button>

              <button
                onClick={switchCamera}
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 font-semibold hover:bg-white/10"
              >
                <SwitchCamera className="h-5 w-5" />
                Schimbă camera
              </button>
            </div>
          </div>

          <div className="relative mt-6 overflow-hidden rounded-2xl border border-white/10 bg-black sm:rounded-3xl">
            <video
              ref={videoRef}
              className="h-[52vh] min-h-[320px] w-full object-cover sm:h-[420px]"
              muted
              playsInline
            />
            {isScanning && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6">
                <div className="relative h-32 w-full max-w-xl rounded-2xl border-2 border-emerald-300/80 shadow-[0_0_0_999px_rgba(0,0,0,0.28)] sm:h-36">
                  <p className="absolute left-0 right-0 top-full mt-3 text-center text-xs font-semibold text-emerald-100">
                    Încadrează barele și cifrele tipărite dedesubt
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm font-semibold text-gray-200">
            {scanStatus}
            {isOcrAnalyzing && (
              <span className="ml-2 text-emerald-300">Verific imaginea...</span>
            )}
          </div>

          {pendingBarcodeConfirmation && (
            <div
              ref={confirmationPanelRef}
              className="mt-4 scroll-mt-4 rounded-2xl border border-yellow-300/30 bg-yellow-300/10 p-4 sm:scroll-mt-6"
            >
              <p className="text-sm font-black uppercase tracking-wide text-yellow-100">
                Verifică codul citit
              </p>
              <code className="mt-3 block rounded-xl border border-yellow-300/25 bg-black/40 px-3 py-3 text-center font-mono text-xl font-black tracking-[0.12em] text-white sm:text-2xl sm:tracking-[0.16em]">
                {pendingBarcodeConfirmation.barcode}
              </code>
              <p className="mt-3 text-sm leading-6 text-gray-300">
                Compară cifrele cu cele tipărite sub codul de bare. Caut produsul doar după confirmarea ta.
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <button
                  type="button"
                  onClick={confirmPendingBarcode}
                  disabled={isLookingUp}
                  className="rounded-2xl bg-yellow-300 px-5 py-3 font-semibold text-black hover:bg-yellow-200 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isLookingUp ? "Caut..." : "Da, caută produsul"}
                </button>
                <button
                  type="button"
                  onClick={rejectPendingBarcode}
                  className="rounded-2xl border border-white/10 px-5 py-3 font-semibold text-white hover:bg-white/10"
                >
                  Nu, rescanez
                </button>
                <button
                  type="button"
                  onClick={editPendingBarcode}
                  className="rounded-2xl border border-white/10 px-5 py-3 font-semibold text-white hover:bg-white/10"
                >
                  Corectez manual
                </button>
              </div>
            </div>
          )}

          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            {!isScanning ? (
              <button
                onClick={() => startScanner()}
                className="rounded-2xl bg-emerald-400 px-6 py-4 font-semibold text-black hover:bg-emerald-300"
              >
                Pornește camera
              </button>
            ) : (
              <button
                onClick={stopScanner}
                className="rounded-2xl border border-red-400/30 px-6 py-4 font-semibold text-red-300 hover:bg-red-400/10"
              >
                Oprește camera
              </button>
            )}

            <button
              onClick={restartScanner}
              className="rounded-2xl border border-white/10 px-6 py-4 font-semibold hover:bg-white/10"
            >
              Repornește scannerul
            </button>

            {isScanning && torchSupported && (
              <button
                onClick={toggleTorch}
                className="rounded-2xl border border-yellow-300/30 px-6 py-4 font-semibold text-yellow-200 hover:bg-yellow-300/10"
              >
                {torchEnabled ? "Oprește lanterna" : "Pornește lanterna"}
              </button>
            )}

          </div>

          <div className="mt-6 rounded-2xl border border-white/10 bg-black/30 p-4">
            <label className="text-sm font-semibold text-gray-300">
              Introdu codul manual
            </label>

            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <input
                value={barcode}
                onChange={(e) => setBarcode(e.target.value)}
                placeholder="Ex: 5449000000996"
                className="min-w-0 flex-1 rounded-2xl border border-white/10 bg-[#0b0f14] px-4 py-3 text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
              />
              <button
                onClick={() => lookupBarcode(barcode, "manual")}
                disabled={isLookingUp}
                className="rounded-2xl bg-emerald-400 px-5 py-3 font-semibold text-black hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isLookingUp ? "Se caută..." : "Caută produsul"}
              </button>
              <Link
                href="/scan"
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-5 py-3 font-semibold text-white transition hover:border-cyan-300/50 hover:bg-white/10"
              >
                <Search size={18} />
                Caută după nume
              </Link>
            </div>
          </div>

          <div className="mt-6 rounded-3xl border border-yellow-300/20 bg-yellow-300/10 p-5">
            <h2 className="text-xl font-bold text-yellow-300">
              Pentru o scanare reușită
            </h2>

            <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-gray-300">
              <li>Folosește telefonul și camera din spate.</li>
              <li>Ține codul la 15–30 cm.</li>
              <li>Ține produsul nemișcat câteva clipe.</li>
              <li>Folosește lanterna doar dacă lumina este slabă.</li>
            </ul>
          </div>

          {message && (
            <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4 text-emerald-300">
              {message}
            </div>
          )}

          {billingGate && (
            <div className="mt-6 rounded-2xl border border-yellow-300/30 bg-yellow-300/10 p-5 text-yellow-100">
              <h2 className="text-xl font-black text-yellow-200">
                Limita gratuită a fost atinsă
              </h2>
              <p className="mt-2 text-sm leading-6">
                Ai folosit {billingGate.usage?.monthlyScansUsed ?? billingGate.usage?.weeklyScansUsed ?? 0}/
                  {billingGate.usage?.monthlyScanLimit ?? billingGate.usage?.weeklyScanLimit ?? 5} scanări gratuite luna aceasta.
                  Pro deblochează scanări nelimitate.
              </p>
              <Link
                href="/pricing"
                className="mt-4 inline-flex rounded-lg bg-emerald-400 px-4 py-2.5 font-black text-black hover:bg-emerald-300"
              >
                Vezi planurile
              </Link>
            </div>
          )}

          {visualCandidate && !foundProduct && (
            <div className="mt-6 rounded-3xl border border-yellow-300/30 bg-yellow-300/10 p-5">
              <p className="text-sm font-semibold text-yellow-300">
                Produs probabil
              </p>

              <h2 className="mt-2 text-2xl font-bold">
                {visualCandidate.name || "Produs neconfirmat"}
              </h2>

              <p className="mt-2 text-sm text-gray-300">
                Încredere: {visualCandidate.confidence || 0}%
              </p>

              <p className="mt-3 text-gray-300">
                {visualCandidate.message ||
                  "Arată codul de bare pentru date exacte."}
              </p>

              {visualCandidate.barcode && (
                <button
                  type="button"
                  onClick={() => lookupBarcode(visualCandidate.barcode, "visual")}
                  className="mt-4 rounded-2xl bg-yellow-300 px-5 py-3 font-semibold text-black hover:bg-yellow-200"
                >
                  Verifică acest cod de bare
                </button>
              )}

              {visualCandidate.product && (
                <button
                  type="button"
                  onClick={confirmVisualCandidate}
                  className="mt-4 ml-3 rounded-2xl bg-emerald-400 px-5 py-3 font-semibold text-black hover:bg-emerald-300"
                >
                  Confirmă produsul
                </button>
              )}
            </div>
          )}

          {foundProduct && (
            <div
              ref={resultPanelRef}
              className="mt-6 scroll-mt-4 rounded-3xl border border-white/10 bg-black/30 p-5 sm:scroll-mt-6"
            >
              <div className="grid gap-5 md:grid-cols-[160px_1fr]">
                <ProductImage
                  src={getImageUrl(foundProduct.image)}
                  alt={foundProduct.name}
                  containerClassName="h-40 w-full rounded-2xl"
                  imageClassName="object-contain p-3"
                  fallbackClassName="text-5xl"
                />

                <div>
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-full bg-emerald-400 px-3 py-1 text-sm font-bold text-black">
                      {foundProduct.score || "-"}/10
                    </span>

                    <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                      {foundProduct.category || "Categorie necunoscută"}
                    </span>

                    {foundProduct.barcode && (
                      <span className="rounded-full border border-white/10 px-3 py-1 text-sm text-gray-300">
                        {foundProduct.barcode}
                      </span>
                    )}
                  </div>

                  <h2 className="mt-4 text-3xl font-bold">
                    {foundProduct.name}
                  </h2>

                  <p className="mt-2 text-sm text-emerald-300">
                    {foundProduct.priceText === "preț necunoscut"
                      ? "Verifică prețul în magazin"
                      : foundProduct.priceText || "Verifică prețul în magazin"}
                  </p>
                  {foundProduct.priceSource && (
                    <p className="mt-1 text-xs text-gray-500">
                      {[foundProduct.priceStore, foundProduct.priceDate]
                        .filter(Boolean)
                        .join(" · ")}{" "}
                      · Open Prices
                    </p>
                  )}
                  {foundProduct.barcode && (
                    <button
                      type="button"
                      onClick={() => setIsPriceFormOpen((isOpen) => !isOpen)}
                      className="mt-3 text-sm font-semibold text-emerald-300 hover:text-emerald-200"
                    >
                      {isPriceFormOpen ? "Închide" : "Adaugă prețul din magazin"}
                    </button>
                  )}

                  {isPriceFormOpen && (
                    <div className="mt-3 grid gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 sm:grid-cols-[1fr_140px_auto]">
                      <input
                        value={observedStore}
                        onChange={(event) => setObservedStore(event.target.value)}
                        placeholder="Magazin"
                        className="min-w-0 rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
                      />
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        value={observedPrice}
                        onChange={(event) => setObservedPrice(event.target.value)}
                        placeholder="Lei"
                        className="min-w-0 rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none placeholder:text-gray-500 focus:border-emerald-400"
                      />
                      <button
                        type="button"
                        onClick={saveObservedPrice}
                        disabled={isSavingPrice}
                        className="rounded-xl bg-emerald-400 px-4 py-2 text-sm font-bold text-black hover:bg-emerald-300 disabled:opacity-50"
                      >
                        {isSavingPrice ? "Salvez..." : "Salvează"}
                      </button>
                    </div>
                  )}

                  <p className="mt-4 text-gray-300">
                    {foundProduct.reason ||
                      "Produs identificat după codul de bare."}
                  </p>

                  <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                    <button
                      onClick={() => goToResult(foundProduct)}
                      className="rounded-2xl bg-emerald-400 px-6 py-3 font-semibold text-black hover:bg-emerald-300"
                    >
                      Vezi analiza produsului
                    </button>

                    <button
                      onClick={() => addToCart(foundProduct)}
                      disabled={isAddingToCart}
                      className="inline-flex items-center justify-center gap-2 rounded-2xl border border-white/10 px-6 py-3 font-semibold hover:bg-white/10 disabled:cursor-wait disabled:opacity-70"
                    >
                      {isAddingToCart && <Loader2 size={18} className="animate-spin" />}
                      {isAddingToCart ? "Se adaugă..." : "Adaugă în coș"}
                    </button>

                    {(productSource === "openfoodfacts" ||
                      foundProduct.id == null) && (
                      <button
                        onClick={() => importProduct(foundProduct)}
                        disabled={isImporting}
                        className="rounded-2xl border border-yellow-300/40 bg-yellow-300/10 px-6 py-3 font-semibold text-yellow-300 hover:bg-yellow-300/20 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {isImporting
                          ? "Se salvează..."
                          : "Salvează în baza locală"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {!foundProduct && barcode && message && (
            missingBarcodeCandidate ||
            ["openfoodfacts_unavailable", "external_product_not_found", "external_catalog_unavailable"].includes(lookupIssue)
          ) && (
            <div
              ref={missingProductPanelRef}
              className="mt-6 scroll-mt-4 rounded-2xl border border-yellow-300/30 bg-yellow-300/10 p-4 sm:scroll-mt-6 sm:rounded-3xl sm:p-5"
            >
              <p className="text-sm font-black uppercase tracking-wide text-yellow-100">
                Produs nou în România?
              </p>
              <h2 className="mt-2 text-2xl font-black text-yellow-300">
                {lookupIssue === "openfoodfacts_unavailable"
                  ? "Sursa online nu răspunde"
                  : "Ajută-ne să îl adăugăm."}
              </h2>

              <p className="mt-3 text-sm leading-6 text-gray-300 sm:text-base sm:leading-7">
                {lookupIssue === "openfoodfacts_unavailable"
                  ? "Produsul nu este în baza locală, iar verificarea Open Food Facts nu a putut fi făcută acum. Îl poți adăuga manual sau poți încerca din nou."
                  : "Dacă produsul nu apare în catalog, îl poți trimite ca propunere. Mai întâi confirmă că am citit corect codul de bare, apoi faci pozele și îl trimiți la verificare."}
              </p>
              <p className="mt-3 rounded-xl border border-yellow-300/25 bg-black/25 px-4 py-3 text-sm font-bold text-yellow-50">
                După aprobare primești scanare bonus și până la 10 CeCoins automat.
              </p>

              {missingBarcodeCandidate ? (
                <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
                  <p className="text-sm font-bold text-yellow-100">
                    Cod citit de scanner
                  </p>
                  <code className="mt-2 block rounded-xl border border-yellow-300/25 bg-black/40 px-3 py-3 text-center font-mono text-xl font-black tracking-[0.12em] text-white sm:px-4 sm:text-2xl sm:tracking-[0.16em]">
                    {missingBarcodeCandidate.barcode}
                  </code>
                  <p className="mt-3 text-sm leading-6 text-gray-300">
                    Verifică cifrele tipărite sub codul de bare. Dacă sunt corecte,
                    trimitem formularul cu acest cod precompletat.
                  </p>

                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <Link
                      href={buildSubmitProductLink(true)}
                      className="inline-flex items-center justify-center rounded-2xl bg-yellow-300 px-5 py-3 text-center font-semibold text-black hover:bg-yellow-200"
                    >
                      Da, codul e corect
                    </Link>
                    <button
                      type="button"
                      onClick={rescanMissingBarcode}
                      className="rounded-2xl border border-white/10 px-5 py-3 font-semibold text-white hover:bg-white/10"
                    >
                      Nu, rescanez
                    </button>
                    <button
                      type="button"
                      onClick={editMissingBarcode}
                      className="rounded-2xl border border-white/10 px-5 py-3 font-semibold text-white hover:bg-white/10"
                    >
                      Corectez manual
                    </button>
                  </div>
                </div>
              ) : (
                <Link
                  href={buildSubmitProductLink(true)}
                  className="mt-5 inline-flex w-full items-center justify-center rounded-2xl bg-yellow-300 px-6 py-3 text-center font-semibold text-black hover:bg-yellow-200 sm:w-auto"
                >
                  Trimite produsul la verificare
                </Link>
              )}
            </div>
          )}
        </div>
      </section>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-[#0b0f14]/95 px-4 py-3 shadow-2xl backdrop-blur md:hidden">
        <div className="mx-auto flex max-w-xl items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-black uppercase tracking-wide text-cyan-200">
              {mobileStatusTitle}
            </p>
            <p className="mt-0.5 truncate text-sm font-semibold text-gray-200">
              {mobileStatusDetail}
            </p>
          </div>

          {pendingBarcodeConfirmation ? (
            <button
              type="button"
              onClick={confirmPendingBarcode}
              disabled={isLookingUp}
              className="shrink-0 rounded-xl bg-yellow-300 px-4 py-3 text-sm font-black text-black disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLookingUp ? "Caut..." : "Confirmă"}
            </button>
          ) : foundProduct ? (
            <button
              type="button"
              onClick={() => goToResult(foundProduct)}
              className="shrink-0 rounded-xl bg-emerald-400 px-4 py-3 text-sm font-black text-black"
            >
              Analiza
            </button>
          ) : hasMissingProductPrompt ? (
            <Link
              href={buildSubmitProductLink(Boolean(missingBarcodeCandidate))}
              className="shrink-0 rounded-xl bg-yellow-300 px-4 py-3 text-sm font-black text-black"
            >
              Adaugă
            </Link>
          ) : (
            <button
              type="button"
              onClick={isScanning ? stopScanner : () => startScanner()}
              className={`shrink-0 rounded-xl px-4 py-3 text-sm font-black ${
                isScanning
                  ? "border border-red-400/35 text-red-200"
                  : "bg-emerald-400 text-black"
              }`}
            >
              {isScanning ? "Oprește" : "Scanează"}
            </button>
          )}
        </div>
      </div>
    </main>
  );
}

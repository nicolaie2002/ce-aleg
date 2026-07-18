"use client";

import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";
import { useLocale } from "./LocaleProvider";

export function ServiceWorkerRegistration() {
  const { pick } = useLocale();
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const registrationRef = useRef(null);
  const updateRequestedRef = useRef(false);

  useEffect(() => {
    if (
      process.env.NODE_ENV !== "production" ||
      typeof window === "undefined" ||
      !("serviceWorker" in navigator)
    ) {
      return;
    }

    let disposed = false;

    function watchInstallingWorker(registration) {
      const worker = registration.installing;
      if (!worker) return;

      worker.addEventListener("statechange", () => {
        if (
          !disposed &&
          worker.state === "installed" &&
          navigator.serviceWorker.controller
        ) {
          setUpdateAvailable(true);
        }
      });
    }

    function handleControllerChange() {
      if (updateRequestedRef.current) {
        window.location.reload();
      }
    }

    navigator.serviceWorker.addEventListener(
      "controllerchange",
      handleControllerChange
    );

    navigator.serviceWorker
      .register("/sw.js", { scope: "/", updateViaCache: "none" })
      .then((registration) => {
        if (disposed) return;

        registrationRef.current = registration;
        if (registration.waiting && navigator.serviceWorker.controller) {
          setUpdateAvailable(true);
        }

        registration.addEventListener("updatefound", () => {
          watchInstallingWorker(registration);
        });
        watchInstallingWorker(registration);
      })
      .catch((error) => {
        console.warn("Service worker registration failed", error);
      });

    return () => {
      disposed = true;
      navigator.serviceWorker.removeEventListener(
        "controllerchange",
        handleControllerChange
      );
    };
  }, []);

  const handleUpdate = () => {
    const waitingWorker = registrationRef.current?.waiting;
    if (!waitingWorker) return;

    updateRequestedRef.current = true;
    waitingWorker.postMessage({ type: "SKIP_WAITING" });
    setUpdateAvailable(false);
  };

  if (!updateAvailable) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 animate-slide-up"
      role="alert"
      aria-live="polite"
    >
      <div className="ce-card max-w-sm border border-white/10 p-4 shadow-xl">
        <div className="flex items-start gap-3">
          <RefreshCw
            className="mt-0.5 h-5 w-5 flex-shrink-0 text-cyan-400"
            aria-hidden="true"
          />
          <div className="flex-1">
            <p className="text-sm font-medium text-white">
              {pick("Actualizare disponibilă", "Update available")}
            </p>
            <p className="mt-1 text-xs text-white/60">
              {pick(
                "O versiune nouă a aplicației este gata. Reîncarcă pentru a o folosi.",
                "A new version of the app is ready. Reload to use it."
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={handleUpdate}
            aria-label={pick("Instalează actualizarea", "Install update")}
            className="flex-shrink-0 rounded-lg bg-white px-3 py-1.5 text-xs font-bold text-black transition-colors hover:bg-cyan-100"
          >
            {pick("Reîncarcă", "Reload")}
          </button>
        </div>
      </div>
    </div>
  );
}

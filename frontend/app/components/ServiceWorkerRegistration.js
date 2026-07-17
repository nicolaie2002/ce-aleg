"use client";

import { useEffect, useRef, useState } from "react";
import { Workbox } from "workbox-window";

export function ServiceWorkerRegistration() {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const wbRef = useRef(null);

  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || typeof window === "undefined") {
      return;
    }

    const wbInstance = new Workbox("/sw.js", { scope: "/" });
    wbRef.current = wbInstance;

    wbInstance.addEventListener("waiting", () => {
      setUpdateAvailable(true);
    });

    wbInstance.addEventListener("controlling", () => {
      window.location.reload();
    });

    wbInstance.register().catch(() => {});

    return () => {
      wbInstance.removeEventListener("waiting", () => setUpdateAvailable(true));
      wbInstance.removeEventListener("controlling", () => window.location.reload());
    };
  }, []);

  const handleUpdate = () => {
    if (wbRef.current) {
      wbRef.current.messageSkipWaiting();
      setUpdateAvailable(false);
    }
  };

  if (!updateAvailable) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 animate-slide-up"
      role="alert"
      aria-live="polite"
    >
      <div className="ce-card p-4 max-w-sm shadow-xl border border-white/10">
        <div className="flex items-start gap-3">
          <svg
            className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-medium text-white">
              Actualizare disponibilă
            </p>
            <p className="text-xs text-white/60 mt-1">
              O versiune nouă a aplicației e gata. Reîncarcă pentru a o folosi.
            </p>
          </div>
          <button
            onClick={handleUpdate}
            className="px-3 py-1.5 text-xs font-bold text-black bg-white rounded-lg hover:bg-cyan-100 transition-colors flex-shrink-0"
          >
            Reîncarcă
          </button>
        </div>
      </div>
    </div>
  );
}
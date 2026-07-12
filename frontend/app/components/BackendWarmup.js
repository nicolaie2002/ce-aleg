"use client";

import { useEffect } from "react";

const WARMUP_KEY = "cealeg_backend_warmup_at";
const WARMUP_COOLDOWN_MS = 10 * 60 * 1000;

export function BackendWarmup() {
  useEffect(() => {
    const now = Date.now();
    let lastWarmup = 0;

    try {
      lastWarmup = Number(window.localStorage.getItem(WARMUP_KEY) || 0);
    } catch {
      lastWarmup = 0;
    }

    if (Number.isFinite(lastWarmup) && now - lastWarmup < WARMUP_COOLDOWN_MS) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      fetch("/api/backend/health", {
        cache: "no-store",
        keepalive: true,
      })
        .then(() => {
          try {
            window.localStorage.setItem(WARMUP_KEY, String(Date.now()));
          } catch {
            // Ignore storage failures; the request already did its job.
          }
        })
        .catch(() => {
          // Warm-up is opportunistic; user-facing flows handle backend errors separately.
        });
    }, 900);

    return () => window.clearTimeout(timer);
  }, []);

  return null;
}

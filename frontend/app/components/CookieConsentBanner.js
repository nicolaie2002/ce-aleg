"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { BarChart3, Check, Settings2, X } from "lucide-react";
import { useLocale } from "./LocaleProvider";
import {
  ANALYTICS_CONSENT_EVENT,
  ANALYTICS_CONSENT_KEY,
} from "../utils/analytics";
import {
  CONSENT_CHANGE_EVENT,
  CONSENT_MANAGER_EVENT,
  CONSENT_POLICY_VERSION,
  createConsentState,
  getConsentSessionId,
  persistConsent,
  readStoredConsent,
} from "../utils/consent";

const HAS_OPTIONAL_PROVIDER = Boolean(
  process.env.NEXT_PUBLIC_GA_ID
  || process.env.NEXT_PUBLIC_META_PIXEL_ID
  || process.env.NEXT_PUBLIC_TIKTOK_PIXEL_ID
  || process.env.NEXT_PUBLIC_POSTHOG_KEY
);
const STORED_USER_KEY = "cealeg_user";

const CATEGORY_DEFINITIONS = [
  {
    id: "necessary",
    required: true,
    label: ["Necesare", "Necessary"],
    description: ["Sesiune, securitate și alegerea limbii.", "Session, security and language choice."],
  },
  {
    id: "analytics",
    label: ["Statistici", "Analytics"],
    description: ["Ne ajută să înțelegem ce funcționează.", "Helps us understand what works."],
  },
  {
    id: "marketing",
    label: ["Marketing", "Marketing"],
    description: ["Măsurarea campaniilor Meta sau TikTok.", "Measures Meta or TikTok campaigns."],
  },
  {
    id: "functional",
    label: ["Funcționale", "Functional"],
    description: ["Preferințe și funcții opționale personalizate.", "Optional preferences and personalized features."],
  },
];

function hasSignedInAccount() {
  try {
    const storedUser = JSON.parse(localStorage.getItem(STORED_USER_KEY) || "null");
    return Boolean(storedUser?.id);
  } catch {
    return false;
  }
}

function applyProviderConsent(consent) {
  window.gtag?.("consent", "update", {
    analytics_storage: consent.analytics ? "granted" : "denied",
    ad_storage: consent.marketing ? "granted" : "denied",
    ad_user_data: consent.marketing ? "granted" : "denied",
    ad_personalization: consent.marketing ? "granted" : "denied",
  });

  if (consent.marketing) {
    window.fbq?.("grantConsent");
    window.ttq?.grantConsent?.();
  } else {
    window.fbq?.("revokeConsent");
    window.ttq?.revokeConsent?.();
  }
}

function recordConsent(consent) {
  const categories = {
    necessary: true,
    analytics: consent.analytics,
    marketing: consent.marketing,
    functional: consent.functional,
  };
  const requests = [
    fetch("/api/backend/consent/log", {
      method: "POST",
      credentials: "include",
      keepalive: true,
      headers: {
        "Content-Type": "application/json",
        "X-Session-ID": getConsentSessionId(),
      },
      body: JSON.stringify({
        categories,
        version: CONSENT_POLICY_VERSION,
        timestamp: consent.timestamp,
      }),
    }),
  ];

  if (hasSignedInAccount()) {
    for (const type of ["analytics", "marketing", "functional"]) {
      requests.push(fetch("/api/backend/privacy/consent", {
        method: "POST",
        credentials: "include",
        keepalive: true,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type,
          granted: consent[type],
          policyVersion: CONSENT_POLICY_VERSION,
          source: "web-cookie-manager",
        }),
      }));
    }

    requests.push(fetch("/api/backend/account/consent", {
      method: "POST",
      credentials: "include",
      keepalive: true,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analytics: consent.analytics }),
    }));
  }

  void Promise.allSettled(requests);
}

export function CookieConsentBanner() {
  const { pick } = useLocale();
  const titleId = useId();
  const descriptionId = useId();
  const [open, setOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [consent, setConsent] = useState(() => createConsentState());
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => {
    queueMicrotask(() => {
      const stored = readStoredConsent();
      if (stored) {
        setConsent(stored);
        applyProviderConsent(stored);
        return;
      }

      const legacyChoice = localStorage.getItem(ANALYTICS_CONSENT_KEY);
      if (legacyChoice === "accepted" || legacyChoice === "declined") {
        const migrated = persistConsent(createConsentState({
          analytics: legacyChoice === "accepted",
          marketing: legacyChoice === "accepted",
        }));
        setConsent(migrated);
        applyProviderConsent(migrated);
        return;
      }

      setOpen(HAS_OPTIONAL_PROVIDER);
    });

    function openCookieManager() {
      setShowSettings(true);
      setOpen(true);
    }

    window.addEventListener(CONSENT_MANAGER_EVENT, openCookieManager);
    return () => window.removeEventListener(CONSENT_MANAGER_EVENT, openCookieManager);
  }, []);

  function save(nextConsent, message) {
    const saved = persistConsent(createConsentState(nextConsent));
    setConsent(saved);
    recordConsent(saved);
    applyProviderConsent(saved);
    window.dispatchEvent(new CustomEvent(CONSENT_CHANGE_EVENT, { detail: saved }));
    window.dispatchEvent(new Event(ANALYTICS_CONSENT_EVENT));
    setAnnouncement(message);
    setShowSettings(false);
    setOpen(false);
  }

  function acceptAll() {
    save(
      { analytics: true, marketing: true, functional: true },
      pick("Preferințele pentru cookie-uri au fost salvate.", "Cookie preferences saved.")
    );
  }

  function rejectOptional() {
    save(
      { analytics: false, marketing: false, functional: false },
      pick("Cookie-urile opționale au fost refuzate.", "Optional cookies declined.")
    );
  }

  function saveCustom() {
    save(consent, pick("Preferințele pentru cookie-uri au fost salvate.", "Cookie preferences saved."));
  }

  if (!open) {
    return announcement ? (
      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {announcement}
      </p>
    ) : null;
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-[90] px-3 pb-3 sm:px-5 sm:pb-5">
      <div
        className="mx-auto max-w-5xl rounded-lg border border-[color:var(--surface-edge)] bg-[var(--surface-strong)] p-4 text-foreground shadow-[0_24px_80px_rgba(0,0,0,.45)] backdrop-blur-xl"
        role="dialog"
        aria-modal="false"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <div className="flex gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-cyan-300/12 text-cyan-200">
            <BarChart3 size={21} aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id={titleId} className="text-base font-black">
              {pick("Alege cookie-urile opționale", "Choose optional cookies")}
            </h2>
            <p id={descriptionId} className="mt-1 max-w-2xl text-sm leading-6 text-[var(--text-soft)]">
              {pick(
                "Cele necesare păstrează site-ul sigur. Celelalte se activează numai cu acordul tău.",
                "Necessary storage keeps the site secure. Everything else activates only with your consent."
              )}{" "}
              <Link href="/privacy" className="font-bold text-cyan-200 hover:text-foreground">
                {pick("Confidențialitate", "Privacy")}
              </Link>
            </p>
          </div>
        </div>

        {showSettings ? (
          <div className="mt-4 divide-y divide-white/10 border-y border-white/10">
            {CATEGORY_DEFINITIONS.map((category) => (
              <label key={category.id} className="flex min-h-16 items-center justify-between gap-4 py-3">
                <span className="min-w-0">
                  <span className="block text-sm font-black">{pick(...category.label)}</span>
                  <span className="mt-1 block text-xs leading-5 text-[var(--text-soft)]">
                    {pick(...category.description)}
                  </span>
                </span>
                <input
                  type="checkbox"
                  checked={category.required || consent[category.id]}
                  disabled={category.required}
                  onChange={(event) => setConsent((current) => ({
                    ...current,
                    [category.id]: event.target.checked,
                  }))}
                  className="h-5 w-5 shrink-0 accent-cyan-300"
                />
              </label>
            ))}
          </div>
        ) : null}

        <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={rejectOptional}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[color:var(--surface-edge)] px-4 text-sm font-black hover:bg-[var(--surface-faint)]"
          >
            <X size={16} aria-hidden="true" />
            {pick("Refuz opționale", "Reject optional")}
          </button>
          {showSettings ? (
            <button
              type="button"
              onClick={saveCustom}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-cyan-200/40 px-4 text-sm font-black text-cyan-100 hover:bg-cyan-200/10"
            >
              <Check size={16} aria-hidden="true" />
              {pick("Salvează alegerile", "Save choices")}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setShowSettings(true)}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-cyan-200/40 px-4 text-sm font-black text-cyan-100 hover:bg-cyan-200/10"
            >
              <Settings2 size={16} aria-hidden="true" />
              {pick("Personalizează", "Customize")}
            </button>
          )}
          <button
            type="button"
            onClick={acceptAll}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-cyan-200 px-5 text-sm font-black text-slate-950 hover:bg-white"
          >
            <Check size={16} aria-hidden="true" />
            {pick("Accept toate", "Accept all")}
          </button>
        </div>
      </div>
    </div>
  );
}

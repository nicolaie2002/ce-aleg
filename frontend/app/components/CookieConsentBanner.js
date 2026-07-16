"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { BarChart3, X } from "lucide-react";
import { useLocale } from "./LocaleProvider";
import {
  ANALYTICS_CONSENT_EVENT,
  ANALYTICS_CONSENT_KEY,
} from "../utils/analytics";

const GA_ID = process.env.NEXT_PUBLIC_GA_ID || "";
const META_PIXEL_ID = process.env.NEXT_PUBLIC_META_PIXEL_ID || "";
const TIKTOK_PIXEL_ID = process.env.NEXT_PUBLIC_TIKTOK_PIXEL_ID || "";
const HAS_ANALYTICS_PROVIDER = Boolean(GA_ID || META_PIXEL_ID || TIKTOK_PIXEL_ID);
function saveConsent(value) {
  localStorage.setItem(ANALYTICS_CONSENT_KEY, value);

  const granted = value === "accepted";
  window.gtag?.("consent", "update", {
    analytics_storage: granted ? "granted" : "denied",
    ad_storage: granted ? "granted" : "denied",
    ad_user_data: granted ? "granted" : "denied",
    ad_personalization: granted ? "granted" : "denied",
  });

  if (granted) {
    window.fbq?.("grantConsent");
    window.ttq?.grantConsent?.();
  } else {
    window.fbq?.("revokeConsent");
    window.ttq?.revokeConsent?.();
  }

  window.dispatchEvent(new Event(ANALYTICS_CONSENT_EVENT));
}

export function CookieConsentBanner() {
  const { pick } = useLocale();
  const titleId = useId();
  const [choice, setChoice] = useState("loading");

  useEffect(() => {
    queueMicrotask(() => {
      setChoice(localStorage.getItem(ANALYTICS_CONSENT_KEY) || "pending");
    });
  }, []);

  if (!HAS_ANALYTICS_PROVIDER || choice !== "pending") {
    return null;
  }

  function acceptAnalytics() {
    saveConsent("accepted");
    setChoice("accepted");
  }

  function declineAnalytics() {
    saveConsent("declined");
    setChoice("declined");
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-[90] px-3 pb-3 sm:px-5 sm:pb-5">
      <div
        className="mx-auto max-w-5xl rounded-2xl border border-[color:var(--surface-edge)] bg-[var(--surface-strong)] p-4 text-foreground shadow-[0_24px_80px_rgba(0,0,0,.45)] backdrop-blur-xl"
        role="region"
        aria-labelledby={titleId}
      >
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-300/12 text-cyan-200">
              <BarChart3 size={21} />
            </span>
            <div>
              <h2 id={titleId} className="text-base font-black">
                {pick("Ajută-ne să îmbunătățim site-ul", "Help us improve the site")}
              </h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--text-soft)]">
                {pick(
                  "Folosim cookie-uri opționale doar dacă accepți, pentru statistici, erori și măsurarea reclamelor. Poți continua fără tracking.",
                  "We use optional cookies only if you accept, for analytics, errors and ad measurement. You can continue without tracking."
                )}{" "}
                <Link href="/privacy" className="font-bold text-cyan-200 hover:text-foreground">
                  {pick("Confidențialitate", "Privacy")}
                </Link>
              </p>
            </div>
          </div>

          <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={declineAnalytics}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-[color:var(--surface-edge)] px-4 py-3 text-sm font-black hover:bg-[var(--surface-faint)]"
            >
              <X size={16} />
              {pick("Refuz", "Decline")}
            </button>
            <button
              type="button"
              onClick={acceptAnalytics}
              className="rounded-lg bg-cyan-200 px-5 py-3 text-sm font-black text-slate-950 shadow-[0_0_28px_rgba(103,232,249,.18)] hover:bg-white"
            >
              {pick("Accept statistici", "Accept analytics")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

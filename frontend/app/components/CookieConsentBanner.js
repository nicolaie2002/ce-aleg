"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BarChart3, X } from "lucide-react";
import { useLocale } from "./LocaleProvider";

const GA_ID = process.env.NEXT_PUBLIC_GA_ID || "";
const CONSENT_KEY = "cealeg_analytics_consent";

function saveConsent(value) {
  localStorage.setItem(CONSENT_KEY, value);
  window.dispatchEvent(new Event("cealeg:analytics-consent"));
}

export function CookieConsentBanner() {
  const { pick } = useLocale();
  const [choice, setChoice] = useState("loading");

  useEffect(() => {
    queueMicrotask(() => {
      setChoice(localStorage.getItem(CONSENT_KEY) || "pending");
    });
  }, []);

  if (!GA_ID || choice !== "pending") {
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
      <div className="mx-auto max-w-5xl rounded-2xl border border-[color:var(--surface-edge)] bg-[var(--surface-strong)] p-4 text-foreground shadow-[0_24px_80px_rgba(0,0,0,.45)] backdrop-blur-xl">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-300/12 text-cyan-200">
              <BarChart3 size={21} />
            </span>
            <div>
              <h2 className="text-base font-black">
                {pick("Ajută-ne să îmbunătățim site-ul", "Help us improve the site")}
              </h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--text-soft)]">
                {pick(
                  "Folosim Google Analytics doar dacă accepți, pentru statistici anonime despre pagini și erori. Poți continua fără tracking.",
                  "We use Google Analytics only if you accept, for anonymous page and error statistics. You can continue without tracking."
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

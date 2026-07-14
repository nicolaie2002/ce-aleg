"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Crown, RefreshCw } from "lucide-react";
import { API_URL } from "../../config";
import { AppHeader } from "../../components/AppHeader";
import { useLocale } from "../../components/LocaleProvider";
import { readApiJson } from "../../utils/apiResponse";
import { trackEvent } from "../../utils/analytics";

export default function BillingSuccessPage() {
  const { pick } = useLocale();
  const trackedPlanRef = useRef("");
  const [plan, setPlan] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/billing/status?sync=stripe`)
      .then((response) => (response.ok ? readApiJson(response) : null))
      .then((data) => {
        const nextPlan = data?.usage?.plan || "";

        setPlan(nextPlan);

        if (nextPlan && nextPlan !== "free" && trackedPlanRef.current !== nextPlan) {
          trackedPlanRef.current = nextPlan;
          trackEvent("subscription_started", {
            plan: nextPlan,
            source: "billing_success",
          });
        }
      })
      .catch(() => setPlan(""))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <main className="min-h-screen text-white">
      <AppHeader />
      <section className="ce-shell ce-page">
        <div className="mx-auto max-w-2xl rounded-2xl border border-cyan-300/25 bg-cyan-300/10 p-7 shadow-2xl">
          <p className="flex items-center gap-2 text-sm font-black text-cyan-100">
            <CheckCircle2 size={18} />
            {pick("Plata confirmata", "Payment confirmed")}
          </p>
          <h1 className="mt-4 text-4xl font-black">
            {pick("Abonamentul tău este pregătit.", "Your subscription is ready.")}
          </h1>
          <p className="mt-4 leading-7 text-cyan-50/85">
            {isLoading
              ? pick(
                  "Sincronizam confirmarea de la Stripe. Dureaza doar câteva secunde.",
                  "We are syncing the Stripe confirmation. This only takes a few seconds."
                )
              : plan
                ? pick(`Plan activ: ${plan.toUpperCase()}.`, `Active plan: ${plan.toUpperCase()}.`)
                : pick(
                    "Stripe a confirmat plata. Dacă planul nu apare imediat, reîncarcă dashboard-ul in câteva secunde.",
                    "Stripe confirmed the payment. If the plan does not appear immediately, refresh the dashboard in a few seconds."
                  )}
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
            >
              <Crown size={18} />
              {pick("Mergi la dashboard", "Go to dashboard")}
            </Link>
            <Link
              href="/pricing"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-5 py-3 font-black text-white hover:bg-white/10"
            >
              {isLoading ? <RefreshCw className="animate-spin" size={18} /> : null}
              {pick("Vezi planurile", "View plans")}
              <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

"use client";

import Link from "next/link";
import { ArrowRight, CreditCard } from "lucide-react";
import { AppHeader } from "../../components/AppHeader";
import { useLocale } from "../../components/LocaleProvider";

export default function BillingCancelPage() {
  const { pick } = useLocale();

  return (
    <main className="min-h-screen text-white">
      <AppHeader />
      <section className="ce-shell ce-page">
        <div className="mx-auto max-w-2xl rounded-2xl border border-white/10 bg-white/[0.045] p-7 shadow-2xl">
          <p className="flex items-center gap-2 text-sm font-black text-yellow-100">
            <CreditCard size={18} />
            {pick("Plata a fost anulata", "Payment was cancelled")}
          </p>
          <h1 className="mt-4 text-4xl font-black">
            {pick("Poti alege planul oricand esti pregatit.", "You can choose a plan whenever you are ready.")}
          </h1>
          <p className="mt-4 leading-7 text-gray-300">
            {pick(
              "Contul tau ramane neschimbat. Poti continua pe Free sau poti incerca din nou plata.",
              "Your account stays unchanged. You can continue on Free or try checkout again."
            )}
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/pricing"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
            >
              {pick("Înapoi la planuri", "Back to plans")}
              <ArrowRight size={18} />
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center rounded-lg border border-white/15 px-5 py-3 font-black text-white hover:bg-white/10"
            >
              {pick("Dashboard", "Dashboard")}
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

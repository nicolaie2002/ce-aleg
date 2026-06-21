"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowRight, RotateCcw } from "lucide-react";
import { AppHeader } from "./components/AppHeader";
import { useLocale } from "./components/LocaleProvider";

export default function ErrorPage({ error, reset }) {
  const { pick } = useLocale();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="min-h-screen text-white">
      <AppHeader />
      <section className="ce-shell ce-page">
        <div className="mx-auto max-w-2xl rounded-2xl border border-red-300/25 bg-red-400/10 p-7 shadow-2xl">
          <p className="flex items-center gap-2 text-sm font-black text-red-100">
            <AlertTriangle size={18} />
            {pick("Ceva nu a mers bine", "Something went wrong")}
          </p>
          <h1 className="mt-4 text-4xl font-black">
            {pick("Reincarca pagina sau revino in dashboard.", "Reload the page or return to dashboard.")}
          </h1>
          <p className="mt-4 leading-7 text-red-50/80">
            {pick(
              "Datele tale sunt in siguranta. Daca problema persista, contacteaza suportul.",
              "Your data is safe. If the problem continues, contact support."
            )}
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => reset()}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
            >
              <RotateCcw size={18} />
              {pick("Incearca din nou", "Try again")}
            </button>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-5 py-3 font-black text-white hover:bg-white/10"
            >
              {pick("Dashboard", "Dashboard")}
              <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

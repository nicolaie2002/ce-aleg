"use client";

import * as Sentry from "@sentry/nextjs";
import Link from "next/link";
import { useEffect } from "react";
import { AlertTriangle, ArrowRight, RotateCcw } from "lucide-react";
import { AppHeader } from "./components/AppHeader";
import { useLocale } from "./components/LocaleProvider";

type LocaleApi = {
  pick: (romanian: string, english: string) => string;
};

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { pick } = useLocale() as unknown as LocaleApi;

  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <main className="min-h-screen text-white">
      <AppHeader actionLabel={pick("Scanează", "Scan")} />
      <section className="ce-shell ce-page">
        <div className="mx-auto max-w-2xl rounded-lg border border-red-300/25 bg-red-400/10 p-7 shadow-2xl">
          <p className="flex items-center gap-2 text-sm font-black text-red-100">
            <AlertTriangle aria-hidden="true" size={18} />
            {pick("Ceva nu a mers bine", "Something went wrong")}
          </p>
          <h1 className="mt-4 text-4xl font-black">
            {pick(
              "Reîncarcă pagina sau revino în panoul de control.",
              "Reload the page or return to your dashboard."
            )}
          </h1>
          <p className="mt-4 leading-7 text-red-50/80">
            {pick(
              "Datele tale sunt în siguranță. Dacă problema persistă, contactează echipa de suport.",
              "Your data is safe. If the problem continues, contact support."
            )}
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={reset}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
            >
              <RotateCcw aria-hidden="true" size={18} />
              {pick("Încearcă din nou", "Try again")}
            </button>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-5 py-3 font-black text-white hover:bg-white/10"
            >
              {pick("Panou de control", "Dashboard")}
              <ArrowRight aria-hidden="true" size={18} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

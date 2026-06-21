"use client";

import Link from "next/link";
import { ArrowRight, SearchX } from "lucide-react";
import { AppHeader } from "./components/AppHeader";
import { useLocale } from "./components/LocaleProvider";

export default function NotFound() {
  const { pick } = useLocale();

  return (
    <main className="min-h-screen text-white">
      <AppHeader />
      <section className="ce-shell ce-page">
        <div className="mx-auto max-w-2xl rounded-2xl border border-white/10 bg-white/[0.045] p-7 shadow-2xl">
          <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
            <SearchX size={18} />
            404
          </p>
          <h1 className="mt-4 text-4xl font-black">
            {pick("Pagina nu exista.", "This page does not exist.")}
          </h1>
          <p className="mt-4 leading-7 text-gray-300">
            {pick(
              "Linkul poate fi gresit sau pagina a fost mutata. Revino in dashboard sau scaneaza un produs nou.",
              "The link may be wrong or the page moved. Return to dashboard or scan a new product."
            )}
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
            >
              {pick("Mergi la dashboard", "Go to dashboard")}
              <ArrowRight size={18} />
            </Link>
            <Link
              href="/barcode-scan"
              className="inline-flex items-center justify-center rounded-lg border border-white/15 px-5 py-3 font-black text-white hover:bg-white/10"
            >
              {pick("Scaneaza codul", "Scan barcode")}
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

"use client";

import Link from "next/link";
import { ArrowLeft, Clock3, Mail, MessageCircle, ShieldCheck } from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { useLocale } from "../components/LocaleProvider";

export default function SupportPage() {
  const { pick } = useLocale();

  return (
    <main className="min-h-screen text-white">
      <AppHeader />
      <section className="ce-shell ce-page">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
        >
          <ArrowLeft size={16} />
          {pick("Înapoi la dashboard", "Back to dashboard")}
        </Link>

        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-start">
          <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-7 shadow-2xl">
            <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
              <MessageCircle size={18} />
              {pick("Suport", "Support")}
            </p>
            <h1 className="mt-4 text-4xl font-black md:text-5xl">
              {pick("Ai nevoie de ajutor?", "Need help?")}
            </h1>
            <p className="mt-4 max-w-2xl leading-8 text-gray-300">
              {pick(
                "Scrie-ne pentru probleme de cont, abonament, scanare, produse greșite sau ștergerea datelor.",
                "Contact us for account, subscription, scan, wrong product or data deletion issues."
              )}
            </p>
            <a
              href="mailto:contact@cealeg.shop?subject=Suport%20Ce%20aleg"
              className="mt-7 inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
            >
              <Mail size={18} />
              contact@cealeg.shop
            </a>
          </div>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
              <Clock3 className="text-cyan-200" />
              <h2 className="mt-4 text-xl font-black">
                {pick("Raspuns rapid", "Fast response")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                {pick(
                  "Răspundem cât mai repede pentru probleme de cont, plată, scanare sau produse identificate greșit.",
                  "We reply as quickly as possible for account, payment, scan or incorrect product issues."
                )}
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
              <ShieldCheck className="text-cyan-200" />
              <h2 className="mt-4 text-xl font-black">
                {pick("Include detalii utile", "Include useful details")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                {pick(
                  "Trimite emailul contului, pagina unde ai văzut problema și, dacă poți, o captură de ecran.",
                  "Send the account email, the page where the issue happened and, if possible, a screenshot."
                )}
              </p>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

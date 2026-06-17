"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, MapPin, Store } from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";

const stores = [
  {
    id: "lidl",
    name: "Lidl",
    tagline: "Calitate la pret bun",
  },
  {
    id: "kaufland",
    name: "Kaufland",
    tagline: "Totul pentru cumparaturi mari",
  },
  {
    id: "carrefour",
    name: "Carrefour",
    tagline: "Alternative pentru fiecare buget",
  },
  {
    id: "mega",
    name: "Mega Image",
    tagline: "Alegeri rapide de zi cu zi",
  },
  {
    id: "profi",
    name: "Profi",
    tagline: "Optiuni aproape de tine",
  },
  {
    id: "penny",
    name: "Penny",
    tagline: "Preturi mici, comparatii clare",
  },
  {
    id: "local",
    name: "Market local",
    tagline: "Magazine independente",
  },
  {
    id: "any",
    name: "Orice magazin",
    tagline: "Recomandari generale",
  },
];

export default function StorePage() {
  const { pick } = useLocale();
  const [selectedStore, setSelectedStore] = useState("");

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/dashboard" actionLabel="Dashboard" />
      <section className="ce-shell ce-page flex flex-col">
        <div className="ce-store-panel ce-lifted-shell ce-reveal overflow-hidden rounded-2xl border shadow-2xl">
          <div className="ce-store-panel-head border-b p-6">
            <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-cyan-200">
              <MapPin className="h-4 w-4" />{" "}
              {pick("Alege magazinul", "Choose the store")}
            </p>

            <h1 className="text-3xl font-black md:text-5xl">
              {pick("Unde faci cumparaturile acum?", "Where are you shopping now?")}
            </h1>

            <p className="mt-4 max-w-2xl text-gray-300">
              {pick(
                "Selectia ajuta aplicatia sa ordoneze mai bine alternativele si lista de cumparaturi.",
                "This helps the app rank alternatives and your shopping list better."
              )}
            </p>
          </div>

          <div className="grid gap-4 p-6 sm:grid-cols-2 lg:grid-cols-4 2xl:gap-6">
            {stores.map((store) => (
              <InteractiveSurface
                as="button"
                key={store.id}
                type="button"
                onClick={() => setSelectedStore(store.id)}
                className={`ce-store-card ce-store-card-${store.id} group relative min-h-44 overflow-hidden rounded-2xl border text-left shadow-xl transition hover:-translate-y-1 xl:min-h-56 ${
                  selectedStore === store.id
                    ? "border-cyan-200 ring-2 ring-cyan-200/30"
                    : "border-white/10 hover:border-cyan-300/50"
                }`}
              >
                <span className={`ce-store-brand-visual ce-store-brand-${store.id}`} />
                <span className="absolute inset-0 bg-gradient-to-t from-black/88 via-black/30 to-transparent" />
                {selectedStore === store.id && (
                  <span className="absolute right-4 top-4 rounded-full bg-cyan-200 p-2 text-black">
                    <Check className="h-4 w-4" />
                  </span>
                )}
                <span className="absolute inset-x-4 top-4">
                  <span className="ce-store-wordmark">{store.name}</span>
                </span>
                <span className="absolute bottom-4 left-4 right-4">
                  <span className="block text-2xl font-black text-white">{store.name}</span>
                  <span className="mt-1 block text-sm text-gray-200">
                    {pick(store.tagline, store.id === "any" ? "General recommendations" : "Store-based recommendations")}
                  </span>
                </span>
              </InteractiveSurface>
            ))}
          </div>

          <div className="flex flex-col gap-3 border-t border-white/10 p-6 sm:flex-row">
            <Link
              href={selectedStore ? `/scan?store=${selectedStore}` : "#"}
              className={`inline-flex items-center justify-center gap-2 rounded-lg px-6 py-3 text-center font-black transition ${
                selectedStore
                  ? "bg-white text-black hover:bg-cyan-100"
                  : "cursor-not-allowed bg-white/10 text-gray-500"
              }`}
            >
              <Store className="h-5 w-5" /> {pick("Continua", "Continue")}
            </Link>

            <Link
              href="/scan?store=any"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-6 py-3 text-center font-bold text-white transition hover:bg-white/10"
            >
              {pick("Sari peste", "Skip")} <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

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
    image:
      "https://images.unsplash.com/photo-1604719312566-8912e9227c6a?auto=format&fit=crop&q=80&w=900",
  },
  {
    id: "kaufland",
    name: "Kaufland",
    image:
      "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=900",
  },
  {
    id: "carrefour",
    name: "Carrefour",
    image:
      "https://images.unsplash.com/photo-1578916171728-46686eac8d58?auto=format&fit=crop&q=80&w=900",
  },
  {
    id: "mega",
    name: "Mega Image",
    image:
      "https://images.unsplash.com/photo-1534723452862-4c874018d66d?auto=format&fit=crop&q=80&w=900",
  },
  {
    id: "profi",
    name: "Profi",
    image:
      "https://images.unsplash.com/photo-1583258292688-d0213dc5a3a8?auto=format&fit=crop&q=80&w=900",
  },
  {
    id: "penny",
    name: "Penny",
    image:
      "https://images.unsplash.com/photo-1516594798947-e65505dbb29d?auto=format&fit=crop&q=80&w=900",
  },
  {
    id: "local",
    name: "Market local",
    image:
      "https://images.unsplash.com/photo-1566385101042-1a0aa0c1268c?auto=format&fit=crop&q=80&w=900",
  },
  {
    id: "any",
    name: "Orice magazin",
    image:
      "https://images.unsplash.com/photo-1601599963565-b7f49cfca6a4?auto=format&fit=crop&q=80&w=900",
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
                className={`ce-store-card group relative min-h-44 overflow-hidden rounded-2xl border text-left shadow-xl transition hover:-translate-y-1 xl:min-h-56 ${
                  selectedStore === store.id
                    ? "border-cyan-200 ring-2 ring-cyan-200/30"
                    : "border-white/10 hover:border-cyan-300/50"
                }`}
              >
                <span
                  className="absolute inset-0 bg-cover bg-center transition duration-500 group-hover:scale-105"
                  style={{ backgroundImage: `url(${store.image})` }}
                />
                <span className="absolute inset-0 bg-gradient-to-t from-black/92 via-black/56 to-black/14" />
                {selectedStore === store.id && (
                  <span className="absolute right-4 top-4 rounded-full bg-cyan-200 p-2 text-black">
                    <Check className="h-4 w-4" />
                  </span>
                )}
                <span className="absolute bottom-4 left-4 right-4">
                  <span className="block text-2xl font-black text-white">{store.name}</span>
                  <span className="mt-1 block text-sm text-gray-200">
                    {store.id === "any"
                      ? pick("Recomandari generale", "General recommendations")
                      : pick("Recomandari pentru magazin", "Store-based recommendations")}
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

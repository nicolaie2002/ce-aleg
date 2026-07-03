"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Check, MapPin, Store } from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";

const stores = [
  {
    id: "lidl",
    name: "Lidl",
    tagline: "Calitate la preț bun",
    logo: "/stores/lidl.png",
  },
  {
    id: "kaufland",
    name: "Kaufland",
    tagline: "Totul pentru cumpărături mari",
    logo: "/stores/kaufland.png",
  },
  {
    id: "carrefour",
    name: "Carrefour",
    tagline: "Alternative pentru fiecare buget",
    logo: "/stores/carrefour.png",
  },
  {
    id: "mega",
    name: "Mega Image",
    tagline: "Alegeri rapide de zi cu zi",
    logo: "/stores/mega-image.png",
  },
  {
    id: "profi",
    name: "Profi",
    tagline: "Opțiuni aproape de tine",
    logo: "/stores/profi.png",
  },
  {
    id: "penny",
    name: "Penny",
    tagline: "Prețuri mici, comparații clare",
    logo: "/stores/penny.png",
  },
  {
    id: "local",
    name: "Market local",
    tagline: "Magazine independente",
    logo: "/stores/market-local.png",
  },
  {
    id: "any",
    name: "Orice magazin",
    tagline: "Recomandări generale",
    logo: "/stores/any-store.png",
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
              {pick("Unde faci cumpărăturile acum?", "Where are you shopping now?")}
            </h1>

            <p className="mt-4 max-w-2xl text-gray-300">
              {pick(
                "Selecția ajută aplicația să ordoneze mai bine alternativele și lista de cumpărături.",
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
                className={`ce-store-card ce-store-logo-card group relative flex min-h-[17rem] flex-col overflow-hidden rounded-2xl border p-4 text-center shadow-xl transition hover:-translate-y-1 ${
                  selectedStore === store.id
                    ? "border-cyan-200 ring-2 ring-cyan-200/30"
                    : "border-white/10 hover:border-cyan-300/50"
                }`}
              >
                {selectedStore === store.id && (
                  <span className="absolute right-4 top-4 z-10 rounded-full bg-cyan-200 p-2 text-black shadow-lg">
                    <Check className="h-4 w-4" />
                  </span>
                )}
                <span className="ce-store-logo-frame">
                  <Image
                    src={store.logo}
                    alt={`${store.name} logo`}
                    width={420}
                    height={250}
                    className="ce-store-logo"
                    loading="lazy"
                    unoptimized
                  />
                </span>
                <span className="mt-4 flex flex-1 flex-col items-center justify-center">
                  <span className="ce-store-title">{store.name}</span>
                  <span className="ce-store-tagline">
                    {pick(
                      store.tagline,
                      store.id === "any"
                        ? "General recommendations"
                        : "Store-based recommendations"
                    )}
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
              <Store className="h-5 w-5" /> {pick("Continuă", "Continue")}
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

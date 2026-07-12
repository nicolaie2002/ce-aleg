"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  ArrowRight,
  Barcode,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Gift,
  PackagePlus,
  ScanLine,
  Store,
} from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";

function completeOnboarding(href) {
  try {
    window.localStorage.setItem("cealeg_onboarding_completed", "1");
  } catch {
    // Ignore storage errors; navigation is the important part.
  }

  window.location.assign(href);
}

export default function OnboardingPage() {
  const { pick } = useLocale();
  const [activeIndex, setActiveIndex] = useState(0);

  const steps = useMemo(
    () => [
      {
        eyebrow: pick("Pasul 1", "Step 1"),
        title: pick("Alege magazinul.", "Pick the store."),
        text: pick(
          "Lidl, Kaufland, Carrefour, Mega sau alt magazin. Așa primești alternative mai potrivite pentru raftul unde ești.",
          "Lidl, Kaufland, Carrefour, Mega or another store. This keeps alternatives closer to the shelf you are in."
        ),
        href: "/store",
        cta: pick("Aleg magazinul", "Pick store"),
        icon: Store,
        image: "/products/iaurt-natural-lidl.jpg",
        accent: "border-cyan-300/30 bg-cyan-300/10 text-cyan-100",
      },
      {
        eyebrow: pick("Pasul 2", "Step 2"),
        title: pick("Scanează codul.", "Scan the barcode."),
        text: pick(
          "Confirmi codul citit de cameră, apoi vezi scorul, eticheta și alternativele.",
          "Confirm the code read by the camera, then see the score, label and alternatives."
        ),
        href: "/barcode-scan",
        cta: pick("Încep scanarea", "Start scanning"),
        icon: Barcode,
        image: "/products/skyr.webp",
        accent: "border-emerald-300/30 bg-emerald-300/10 text-emerald-100",
      },
      {
        eyebrow: pick("Pasul 3", "Step 3"),
        title: pick("Produs lipsă? Primești CeCoins.", "Missing product? Earn CeCoins."),
        text: pick(
          "Adaugi poze cu ambalajul și tabelul nutrițional. După aprobare, catalogul crește și primești recompensa.",
          "Add package and nutrition-label photos. After approval, the catalog grows and you receive the reward."
        ),
        href: "/submit-product",
        cta: pick("Adaug produs", "Add product"),
        icon: PackagePlus,
        image: "/brand/CeCoin.webp",
        accent: "border-yellow-300/35 bg-yellow-300/10 text-yellow-100",
      },
    ],
    [pick]
  );

  const activeStep = steps[activeIndex];
  const ActiveIcon = activeStep.icon;
  const isLastStep = activeIndex === steps.length - 1;

  function goNext() {
    if (isLastStep) {
      completeOnboarding("/store");
      return;
    }

    setActiveIndex((index) => Math.min(index + 1, steps.length - 1));
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/dashboard" actionLabel="Dashboard" />

      <section className="ce-shell ce-page pb-28">
        <div className="grid min-h-[calc(100svh-9rem)] gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-center">
          <div>
            <Link
              href="/dashboard"
              onClick={() => {
                try {
                  window.localStorage.setItem("cealeg_onboarding_completed", "1");
                } catch {
                  // Navigation still works if storage is unavailable.
                }
              }}
              className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
            >
              <ChevronLeft size={16} />
              {pick("Sari peste", "Skip")}
            </Link>

            <div className="mt-8 inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.05] px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-gray-200">
              <CheckCircle2 size={15} />
              {pick("Start rapid", "Quick start")}
            </div>

            <h1 className="mt-4 max-w-2xl text-4xl font-black leading-tight md:text-6xl">
              {pick("Începe direct la raft.", "Start at the shelf.")}
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-gray-300">
              {pick(
                "Trei pași simpli ca aplicația să fie utilă imediat pe telefon.",
                "Three simple steps so the app feels useful right away on your phone."
              )}
            </p>

            <div className="mt-7 flex gap-2">
              {steps.map((step, index) => (
                <button
                  key={step.title}
                  type="button"
                  onClick={() => setActiveIndex(index)}
                  aria-label={`${pick("Pasul", "Step")} ${index + 1}`}
                  className={`h-2.5 rounded-full transition ${
                    index === activeIndex ? "w-12 bg-cyan-200" : "w-2.5 bg-white/25 hover:bg-white/45"
                  }`}
                />
              ))}
            </div>
          </div>

          <InteractiveSurface className="overflow-hidden rounded-lg border border-white/10 bg-[#111923]/90 shadow-2xl shadow-black/30">
            <div className="grid gap-0 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <div className="relative min-h-[18rem] overflow-hidden bg-black/25 md:min-h-[34rem]">
                <Image
                  src={activeStep.image}
                  alt=""
                  fill
                  priority
                  sizes="(max-width: 768px) 100vw, 42vw"
                  className={`object-cover ${activeStep.image.includes("CeCoin") ? "p-14 object-contain" : ""}`}
                />
                <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(5,8,15,0.05),rgba(5,8,15,0.82))]" />
                <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-black/45 p-3 backdrop-blur">
                  <div className="min-w-0">
                    <p className="text-xs font-black uppercase tracking-wide text-gray-400">
                      {activeStep.eyebrow}
                    </p>
                    <p className="mt-1 truncate text-sm font-black text-white">{activeStep.cta}</p>
                  </div>
                  <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border ${activeStep.accent}`}>
                    <ActiveIcon size={21} />
                  </span>
                </div>
              </div>

              <div className="flex flex-col justify-between p-5 md:p-7">
                <div>
                  <span className={`inline-flex h-12 w-12 items-center justify-center rounded-lg border ${activeStep.accent}`}>
                    <ActiveIcon size={23} />
                  </span>
                  <h2 className="mt-5 text-3xl font-black leading-tight md:text-5xl">
                    {activeStep.title}
                  </h2>
                  <p className="mt-4 text-sm leading-7 text-gray-300 md:text-base">
                    {activeStep.text}
                  </p>

                  <div className="mt-6 grid gap-3">
                    {[
                      [ScanLine, pick("scanare rapidă", "fast scan")],
                      [Gift, pick("CeCoins pentru contribuții", "CeCoins for contributions")],
                      [Store, pick("magazine din România", "Romanian stores")],
                    ].map(([Icon, label]) => (
                      <div key={label} className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-3">
                        <Icon size={18} className="shrink-0 text-cyan-200" />
                        <span className="min-w-0 truncate text-sm font-bold text-gray-200">{label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-8 grid gap-3 sm:grid-cols-[auto_1fr]">
                  <button
                    type="button"
                    onClick={() => setActiveIndex((index) => Math.max(index - 1, 0))}
                    disabled={activeIndex === 0}
                    className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg border border-white/12 px-4 py-3 text-sm font-black text-white hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <ChevronLeft size={18} />
                    {pick("Înapoi", "Back")}
                  </button>
                  <button
                    type="button"
                    onClick={goNext}
                    className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-black text-black hover:bg-cyan-100"
                  >
                    {isLastStep ? pick("Încep", "Start") : pick("Mai departe", "Next")}
                    <ChevronRight size={18} />
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => completeOnboarding(activeStep.href)}
                  className="mt-3 inline-flex min-h-12 items-center justify-center gap-2 rounded-lg border border-cyan-300/30 bg-cyan-300/10 px-5 py-3 text-sm font-black text-cyan-100 hover:bg-cyan-300/20"
                >
                  {activeStep.cta}
                  <ArrowRight size={18} />
                </button>
              </div>
            </div>
          </InteractiveSurface>
        </div>
      </section>
    </main>
  );
}

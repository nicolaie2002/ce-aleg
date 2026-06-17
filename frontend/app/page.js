"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BadgeCheck,
  Barcode,
  Camera,
  CheckCircle2,
  Crown,
  ScanLine,
  Search,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Star,
  TrendingDown,
  Zap,
} from "lucide-react";
import { LanguageSwitcher } from "./components/LanguageSwitcher";
import { ThemeSwitcher } from "./components/ThemeSwitcher";
import { InteractiveSurface } from "./components/InteractiveSurface";
import { useLocale } from "./components/LocaleProvider";
import { API_URL } from "./config";

export default function Home() {
  const { pick } = useLocale();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const liveAssistantHref = isAuthenticated
    ? "/live-assistant"
    : "/login?next=/live-assistant";
  const barcodeHref = isAuthenticated
    ? "/barcode-scan"
    : "/login?next=/barcode-scan";

  useEffect(() => {
    fetch(`${API_URL}/auth/me`)
      .then((response) => setIsAuthenticated(response.ok))
      .catch(() => setIsAuthenticated(false));
  }, []);

  const steps = [
    {
      icon: ScanLine,
      title: pick("Scanezi produsul", "Scan the product"),
      detail: pick(
        "Arati codul de bare sau eticheta camerei telefonului.",
        "Show the barcode or label to your phone camera."
      ),
    },
    {
      icon: Sparkles,
      title: pick("Primești verdictul", "Get the verdict"),
      detail: pick(
        "Vezi rapid scorul, ingredientele importante si ce merita retinut.",
        "See the score, key ingredients and what matters."
      ),
    },
    {
      icon: TrendingDown,
      title: pick("Alegi alternativa", "Choose an alternative"),
      detail: pick(
        "Compari variante mai potrivite pentru buget, zahar, proteina sau ingrediente.",
        "Compare better picks for price, sugar, protein or ingredients."
      ),
    },
  ];

  const capabilities = [
    {
      icon: Barcode,
      label: pick("Coduri de bare", "Barcodes"),
      detail: pick(
        "Identificare rapida din camera si cautare manuala cand codul nu se vede perfect.",
        "Fast camera identification and manual lookup when the code is hard to read."
      ),
    },
    {
      icon: Camera,
      label: pick("Asistent live", "Live assistant"),
      detail: pick(
        "Camera ramane deschisa si te ajuta sa recunosti produsul la raft.",
        "Keep the camera open and recognize products at the shelf."
      ),
    },
    {
      icon: Search,
      label: pick("Cautare dupa preferinte", "Preference search"),
      detail: pick(
        "Cere alternative mai ieftine, fara zahar, mai proteice sau cu ingrediente mai curate.",
        "Ask for cheaper, lower sugar, higher protein or cleaner alternatives."
      ),
    },
  ];

  const metrics = [
    { label: pick("Scor", "Score"), value: "8.7/10", accent: "text-cyan-200" },
    { label: pick("Zahar", "Sugar"), value: "-42%", accent: "text-yellow-200" },
    { label: pick("Proteina", "Protein"), value: "+6g", accent: "text-cyan-200" },
  ];

  return (
    <main className="min-h-screen text-white">
      <section className="ce-home-hero relative overflow-hidden border-b border-white/10">
        <div
          className="absolute inset-0 bg-cover bg-center opacity-70"
          style={{
            backgroundImage:
              "linear-gradient(90deg, rgba(4,8,11,.98) 0%, rgba(4,8,11,.9) 38%, rgba(4,8,11,.48) 100%), url('https://images.unsplash.com/photo-1760463921956-b21cfa5cb2ac?auto=format&fit=crop&q=85&w=2400')",
          }}
        />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_18%,rgba(16,185,129,.22),transparent_30%),radial-gradient(circle_at_80%_20%,rgba(250,204,21,.14),transparent_28%),linear-gradient(180deg,transparent,#070a0e_96%)]" />

        <div className="ce-shell relative z-10 pb-14 pt-5 md:pb-20 md:pt-7">
          <nav className="ce-glass-nav ce-reveal flex flex-wrap items-center justify-between gap-3 rounded-2xl p-3 backdrop-blur-xl">
            <Link href="/" className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-emerald-400 text-black shadow-[0_0_28px_rgba(52,211,153,.22)]">
                <ShoppingCart size={22} strokeWidth={2.5} />
              </span>
              <span>
                <span className="block text-lg font-black leading-none">Ce aleg?</span>
                <span className="text-xs font-semibold text-cyan-100/80">
                  {pick("cumparaturi mai inteligente", "smarter shopping")}
                </span>
              </span>
            </Link>

            <div className="flex flex-wrap items-center justify-end gap-2">
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 rounded-lg border border-yellow-300/35 bg-yellow-300/10 px-3 py-2 text-sm font-black text-yellow-200 hover:bg-yellow-300/20"
              >
                <Crown size={16} />
                {pick("Planuri", "Plans")}
              </Link>
              <LanguageSwitcher />
              <ThemeSwitcher />
              <Link
                href={isAuthenticated ? "/dashboard" : "/login"}
                className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-black text-black hover:bg-cyan-100"
              >
                {isAuthenticated ? pick("Dashboard", "Dashboard") : pick("Intra in cont", "Sign in")}
                <ArrowRight size={16} />
              </Link>
            </div>
          </nav>

          <div className="grid gap-10 pt-12 lg:grid-cols-[minmax(0,1fr)_480px] lg:items-center xl:grid-cols-[minmax(0,1fr)_540px] xl:pt-16">
            <div className="ce-hero-copy ce-reveal ce-reveal-delay-1">
              <div className="ce-hero-pill inline-flex items-center gap-2 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-4 py-2 text-sm font-black text-cyan-100">
                <BadgeCheck size={17} />
                {pick("Verdict rapid inainte sa cumperi", "Quick verdict before you buy")}
              </div>
              <h1 className="mt-6 max-w-5xl text-5xl font-black leading-[1.02] md:text-7xl xl:text-8xl">
                {pick(
                  "Alege produsul mai bun direct la raft.",
                  "Choose the better product at the shelf."
                )}
              </h1>
              <p className="mt-6 max-w-3xl text-lg leading-8 text-gray-200 md:text-xl">
                {pick(
                  "Scanezi un produs, vezi daca merita cumparat si primesti alternative clare pentru bugetul si preferintele tale.",
                  "Scan a product, see if it is worth buying and get clear alternatives for your budget and preferences."
                )}
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                <Link
                  href={liveAssistantHref}
                  className="ce-premium-button inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-4 font-black text-black shadow-[0_0_30px_rgba(103,232,249,.18)] hover:-translate-y-0.5 hover:bg-cyan-100"
                >
                  <Camera className="h-5 w-5" />
                  {pick("Deschide camera", "Open camera")}
                </Link>
                <Link
                  href={barcodeHref}
                  className="ce-hero-secondary-action inline-flex items-center justify-center gap-2 rounded-lg border border-white/18 bg-black/35 px-6 py-4 font-bold text-white backdrop-blur hover:-translate-y-0.5 hover:bg-white/10"
                >
                  <Barcode className="h-5 w-5" />
                  {pick("Scaneaza codul", "Scan barcode")}
                </Link>
                <Link
                  href="/pricing"
                  className="ce-hero-plan-action inline-flex items-center justify-center gap-2 rounded-lg border border-yellow-300/35 bg-yellow-300/10 px-6 py-4 font-bold text-yellow-200 hover:-translate-y-0.5 hover:bg-yellow-300/20"
                >
                  <Crown className="h-5 w-5" />
                  {pick("Vezi planurile", "See plans")}
                </Link>
              </div>

              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-gray-200">
                <span className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-cyan-200" />
                  {pick("Cont protejat", "Protected account")}
                </span>
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-cyan-200" />
                  {pick("Istoric si cos salvate", "Saved history and cart")}
                </span>
                <span className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-cyan-200" />
                  {pick("Recomandari rapide", "Fast recommendations")}
                </span>
              </div>
            </div>

            <div className="relative ce-reveal ce-reveal-delay-2">
              <div className="absolute -inset-5 rounded-[2rem] bg-cyan-300/12 blur-3xl" />
              <InteractiveSurface className="ce-home-demo-card ce-lifted-shell relative overflow-hidden rounded-[1.5rem] border border-white/12 bg-[#0d141b]/92 p-4 shadow-2xl backdrop-blur">
                <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-4">
                  <div>
                    <p className="text-xs font-black uppercase text-cyan-200">
                      {pick("Analiza produs", "Product analysis")}
                    </p>
                    <h2 className="mt-1 text-2xl font-black">
                      {pick("Iaurt grecesc 2%", "Greek yogurt 2%")}
                    </h2>
                  </div>
                  <span className="rounded-full bg-emerald-400 px-3 py-1 text-sm font-black text-black">
                    8.7/10
                  </span>
                </div>

                <div className="grid gap-3 py-4 sm:grid-cols-3">
                  {metrics.map((metric) => (
                    <div key={metric.label} className="rounded-lg border border-white/10 bg-black/28 p-3">
                      <p className="text-xs text-gray-400">{metric.label}</p>
                      <p className={`mt-1 text-2xl font-black ${metric.accent}`}>{metric.value}</p>
                    </div>
                  ))}
                </div>

                <div className="rounded-xl border border-cyan-300/25 bg-cyan-300/10 p-4">
                  <p className="flex items-center gap-2 font-black text-cyan-100">
                    <Star size={18} className="text-yellow-200" />
                    {pick("Recomandare", "Recommendation")}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-cyan-50/85">
                    {pick(
                      "Bun pentru o gustare rapida. Daca vrei mai multa proteina, vezi alternativele recomandate.",
                      "Good for a quick snack. If you want more protein, check the recommended alternatives."
                    )}
                  </p>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <Link
                    href={barcodeHref}
                    className="ce-premium-button inline-flex items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 font-black text-black hover:bg-cyan-100"
                  >
                    <ScanLine size={18} />
                    {pick("Testeaza acum", "Try now")}
                  </Link>
                  <Link
                    href="/alternatives"
                    className="ce-demo-secondary-action inline-flex items-center justify-center gap-2 rounded-lg border border-white/12 px-4 py-3 font-black text-white hover:bg-white/10"
                  >
                    {pick("Vezi alternative", "See alternatives")}
                    <ArrowRight size={18} />
                  </Link>
                </div>
                <span className="ce-scan-line" />
              </InteractiveSurface>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-white/10 bg-[#080d12]">
        <div className="ce-shell grid gap-4 py-8 md:grid-cols-3 xl:py-10">
          {steps.map(({ icon: Icon, title, detail }, index) => (
            <InteractiveSurface
              as="article"
              key={title}
              className={`ce-reveal ce-reveal-delay-${Math.min(index + 1, 3)} rounded-2xl border border-white/10 bg-white/[0.035] p-5 transition hover:-translate-y-1 hover:border-cyan-300/35 hover:bg-white/[0.055]`}
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-cyan-300/12 text-cyan-200">
                <Icon size={22} />
              </span>
              <h2 className="mt-5 text-xl font-black">{title}</h2>
              <p className="mt-2 leading-7 text-gray-400">{detail}</p>
            </InteractiveSurface>
          ))}
        </div>
      </section>

      <section className="bg-[#070a0e]">
        <div className="ce-shell ce-page">
          <div className="grid gap-8 xl:grid-cols-[420px_minmax(0,1fr)] xl:items-start">
            <div>
              <p className="text-sm font-black text-cyan-200">
                {pick("Pentru cumparaturi reale", "For real shopping")}
              </p>
              <h2 className="mt-3 text-4xl font-black leading-tight md:text-5xl">
                {pick(
                  "Tot ce ai nevoie in fata raftului.",
                  "Everything you need in front of the shelf."
                )}
              </h2>
              <p className="mt-4 leading-8 text-gray-300">
                {pick(
                  "Aplicatia este gandita pentru momentele in care vrei un raspuns rapid: merita produsul sau exista o varianta mai buna?",
                  "The app is built for the moment when you need a quick answer: is this product worth it or is there a better option?"
                )}
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {capabilities.map(({ icon: Icon, label, detail }) => (
                <InteractiveSurface
                  as="article"
                  key={label}
                  className="rounded-2xl border border-white/10 bg-[#0d141b] p-5 shadow-xl transition hover:-translate-y-1 hover:border-cyan-300/35"
                >
                  <Icon className="h-6 w-6 text-cyan-200" />
                  <h3 className="mt-5 text-lg font-black">{label}</h3>
                  <p className="mt-2 text-sm leading-6 text-gray-400">{detail}</p>
                </InteractiveSurface>
              ))}
            </div>
          </div>

          <InteractiveSurface className="mt-10 rounded-2xl border border-cyan-300/25 bg-[linear-gradient(135deg,rgba(103,232,249,.14),rgba(250,204,21,.09),rgba(255,255,255,.035))] p-5 md:flex md:items-center md:justify-between md:gap-6 md:p-7">
            <div>
              <p className="text-sm font-black text-cyan-100">
                {pick("Gata de testat", "Ready to test")}
              </p>
              <h2 className="mt-2 text-2xl font-black">
                {pick(
                  "Intra in cont si scaneaza primul produs.",
                  "Sign in and scan your first product."
                )}
              </h2>
            </div>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row md:mt-0">
              <Link
                href={isAuthenticated ? "/dashboard" : "/register"}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
              >
                {isAuthenticated ? pick("Mergi la dashboard", "Go to dashboard") : pick("Creeaza cont", "Create account")}
                <ArrowRight size={18} />
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-yellow-300/35 bg-yellow-300/10 px-5 py-3 font-black text-yellow-100 hover:bg-yellow-300/20"
              >
                <Crown size={18} />
                {pick("Compara planurile", "Compare plans")}
              </Link>
            </div>
          </InteractiveSurface>
        </div>
      </section>

    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  AlertTriangle,
  BadgeCheck,
  Barcode,
  Camera,
  CheckCircle2,
  CircleCheck,
  CircleX,
  Crown,
  Database,
  ScanLine,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  TrendingDown,
  Zap,
} from "lucide-react";
import { LanguageSwitcher } from "./components/LanguageSwitcher";
import { ThemeSwitcher } from "./components/ThemeSwitcher";
import { InteractiveSurface } from "./components/InteractiveSurface";
import { CarbonVaporBackground } from "./components/CarbonVaporBackground";
import { useLocale } from "./components/LocaleProvider";

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
    queueMicrotask(() => {
      try {
        setIsAuthenticated(Boolean(window.localStorage.getItem("cealeg_user")));
      } catch {
        setIsAuthenticated(false);
      }
    });
  }, []);

  const steps = [
    {
      icon: ScanLine,
      title: pick("Scanezi codul de bare", "Scan the barcode"),
      detail: pick(
        "Încadrează codul de bare, iar aplicația identifică produsul din catalog.",
        "Frame the barcode and the app identifies the product from the catalog."
      ),
    },
    {
      icon: Sparkles,
      title: pick("Primești verdictul", "Get the verdict"),
      detail: pick(
        "Vezi rapid scorul, ingredientele importante și ce merită reținut.",
        "See the score, key ingredients and what matters."
      ),
    },
    {
      icon: TrendingDown,
      title: pick("Alegi alternativa", "Choose an alternative"),
      detail: pick(
        "Compari variante mai potrivite pentru buget, zahăr, proteină sau ingrediente.",
        "Compare better picks for price, sugar, protein or ingredients."
      ),
    },
  ];

  const capabilities = [
    {
      icon: Barcode,
      label: pick("Coduri de bare", "Barcodes"),
      detail: pick(
        "Identificare rapidă din cameră și căutare manuală când codul nu se vede perfect.",
        "Fast camera identification and manual lookup when the code is hard to read."
      ),
    },
    {
      icon: Camera,
      label: pick("Asistent vizual AI în curând", "AI visual assistant coming soon"),
      detail: pick(
        "Identificarea produsului după ambalaj va fi activată pentru Pro și Family când serviciul AI este disponibil.",
        "Package-based product identification will be enabled for Pro and Family when the AI service is available."
      ),
    },
    {
      icon: Search,
      label: pick("Căutare după preferințe", "Preference search"),
      detail: pick(
        "Cere alternative mai ieftine, fără zahăr, mai proteice sau cu ingrediente mai curate.",
        "Ask for cheaper, lower sugar, higher protein or cleaner alternatives."
      ),
    },
  ];

  const metrics = [
    { label: pick("Scor", "Score"), value: "8.7/10", accent: "text-cyan-200" },
    { label: pick("Zahăr", "Sugar"), value: "-42%", accent: "text-yellow-200" },
    { label: pick("Proteină", "Protein"), value: "+6g", accent: "text-cyan-200" },
  ];

  const verdictCards = [
    {
      icon: CircleCheck,
      image: "/products/skyr.jpg",
      tone: "border-cyan-300/35 bg-cyan-300/10 text-cyan-100",
      badge: pick("Așa da", "Good pick"),
      title: pick("Skyr simplu", "Plain skyr"),
      score: "8.9",
      detail: pick(
        "Proteină bună, zahăr redus și ingrediente ușor de înțeles.",
        "Good protein, lower sugar and easy-to-understand ingredients."
      ),
      points: [
        pick("mai puțin zahăr", "less sugar"),
        pick("mai multă proteină", "more protein"),
      ],
    },
    {
      icon: AlertTriangle,
      image: "/products/lapte-ovaz.jpg",
      tone: "border-yellow-300/35 bg-yellow-300/10 text-yellow-100",
      badge: pick("Mai verifică", "Check first"),
      title: pick("Băutură vegetală", "Plant drink"),
      score: "6.8",
      detail: pick(
        "Poate fi potrivită, dar compară zahărul, uleiurile și lista de aditivi.",
        "Can be a good fit, but compare sugar, oils and additives."
      ),
      points: [
        pick("verifică zahărul", "check sugar"),
        pick("aditivi de urmărit", "additives to check"),
      ],
    },
    {
      icon: CircleX,
      image: "/products/baton-ovaz.jpg",
      tone: "border-rose-300/35 bg-rose-300/10 text-rose-100",
      badge: pick("Așa nu", "Poor fit"),
      title: pick("Snack foarte dulce", "Very sweet snack"),
      score: "3.4",
      detail: pick(
        "Când scorul e slab, primești variante apropiate din aceeași familie.",
        "When the score is weak, you get close alternatives from the same family."
      ),
      points: [
        pick("zahăr ridicat", "high sugar"),
        pick("caută alternativă", "find alternative"),
      ],
    },
  ];

  return (
    <main className="min-h-screen text-white">
      <section className="ce-home-hero relative overflow-hidden border-b border-white/10">
        <CarbonVaporBackground variant="hero" />
        <div className="ce-hero-carbon-shell absolute inset-0" />

        <div className="ce-shell relative z-10 pb-14 pt-5 md:pb-20 md:pt-7">
          <nav className="ce-glass-nav ce-reveal flex flex-wrap items-center justify-between gap-3 rounded-2xl p-3 backdrop-blur-xl">
            <Link href="/" className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-lg shadow-[0_0_28px_rgba(52,211,153,.22)]">
                <Image
                  src="/icon.png"
                  alt="Ce aleg?"
                  width={88}
                  height={88}
                  className="h-full w-full object-cover"
                  priority
                  unoptimized
                />
              </span>
              <span>
                <span className="block text-lg font-black leading-none text-white">Ce aleg?</span>
                <span className="text-xs font-semibold text-cyan-50/85">
                  {pick("cumpărături mai inteligente", "smarter shopping")}
                </span>
              </span>
            </Link>

            <div className="flex flex-wrap items-center justify-end gap-2">
              <Link
                href="/catalog-romania"
                className="inline-flex items-center gap-2 rounded-lg border border-cyan-300/35 bg-cyan-300/10 px-3 py-2 text-sm font-black text-cyan-100 hover:bg-cyan-300/20"
              >
                <Database size={16} />
                {pick("Catalog", "Catalog")}
              </Link>
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
                {isAuthenticated ? pick("Dashboard", "Dashboard") : pick("Intră în cont", "Sign in")}
                <ArrowRight size={16} />
              </Link>
            </div>
          </nav>

          <div className="grid gap-10 pt-12 lg:grid-cols-[minmax(0,1fr)_480px] lg:items-center xl:grid-cols-[minmax(0,1fr)_540px] xl:pt-16">
            <div className="ce-hero-copy ce-reveal ce-reveal-delay-1">
              <div className="ce-hero-pill inline-flex items-center gap-2 rounded-full border border-cyan-300/30 bg-cyan-300/10 px-4 py-2 text-sm font-black text-cyan-100">
                <BadgeCheck size={17} />
                {pick("Viitorul cumpărăturilor este aici", "The future of shopping is here")}
              </div>
              <h1 className="mt-6 max-w-5xl text-4xl font-black leading-[1.04] sm:text-5xl md:text-7xl xl:text-8xl">
                {pick(
                  "Alege produsul mai bun direct la raft.",
                  "Choose the better product at the shelf."
                )}
              </h1>
              <p className="mt-6 max-w-3xl text-lg leading-8 text-gray-200 md:text-xl">
                {pick(
                  "Scanezi codul de bare, vezi dacă produsul merită cumpărat și primești alternative clare pentru bugetul și preferințele tale.",
                  "Scan the barcode, see if the product is worth buying and get clear alternatives for your budget and preferences."
                )}
              </p>

              <div className="mt-8 grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
                <Link
                  href={barcodeHref}
                  className="ce-premium-button col-span-2 inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-4 font-black text-black shadow-[0_0_30px_rgba(103,232,249,.18)] hover:-translate-y-0.5 hover:bg-cyan-100 sm:col-span-1 sm:px-6"
                >
                  <Barcode className="h-5 w-5" />
                  {pick("Scanează codul", "Scan barcode")}
                </Link>
                <Link
                  href={liveAssistantHref}
                  className="ce-hero-secondary-action inline-flex items-center justify-center gap-2 rounded-lg border border-white/18 bg-black/35 px-3 py-4 text-sm font-bold text-white backdrop-blur hover:-translate-y-0.5 hover:bg-white/10 sm:px-6 sm:text-base"
                >
                  <Camera className="h-5 w-5" />
                  {pick("AI vizual în curând", "AI visual coming soon")}
                </Link>
                <Link
                  href="/pricing"
                  className="ce-hero-plan-action inline-flex items-center justify-center gap-2 rounded-lg border border-yellow-300/35 bg-yellow-300/10 px-3 py-4 text-sm font-bold text-yellow-200 hover:-translate-y-0.5 hover:bg-yellow-300/20 sm:px-6 sm:text-base"
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
                  {pick("Istoric și coș salvate", "Saved history and cart")}
                </span>
                <span className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-cyan-200" />
                  {pick("Recomandări rapide", "Fast recommendations")}
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
                  <span className="rounded-full bg-cyan-200 px-3 py-1 text-sm font-black text-black">
                    8.7/10
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 py-4 sm:gap-3">
                  {metrics.map((metric) => (
                    <div key={metric.label} className="rounded-lg border border-white/10 bg-black/28 p-2 sm:p-3">
                      <p className="text-xs text-gray-400">{metric.label}</p>
                      <p className={`mt-1 text-xl font-black sm:text-2xl ${metric.accent}`}>{metric.value}</p>
                    </div>
                  ))}
                </div>

                <div className="ce-demo-recommendation rounded-xl p-4">
                  <p className="ce-demo-recommendation-title flex items-center gap-2 font-black">
                    <Star size={18} className="text-yellow-200" />
                    {pick("Verdict recomandat", "Suggested verdict")}
                  </p>
                  <p className="ce-demo-recommendation-copy mt-2 text-sm leading-6">
                    {pick(
                      "Potrivit pentru o gustare simplă. Compară alternativele dacă vrei mai multă proteină, zahăr mai puțin sau ingrediente mai curate.",
                      "Good for a simple snack. Compare alternatives if you want more protein, less sugar or cleaner ingredients."
                    )}
                  </p>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <Link
                    href={barcodeHref}
                    className="ce-premium-button inline-flex items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 font-black text-black hover:bg-cyan-100"
                  >
                    <ScanLine size={18} />
                    {pick("Testează acum", "Try now")}
                  </Link>
                  <Link
                    href="/alternatives"
                    className="ce-demo-secondary-action inline-flex items-center justify-center gap-2 rounded-lg border border-white/12 px-4 py-3 font-black text-white hover:bg-white/10"
                  >
                    {pick("Vezi alternative", "See alternatives")}
                    <ArrowRight size={18} />
                  </Link>
                </div>
              </InteractiveSurface>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-white/10 bg-[#080d12]">
        <div className="ce-shell ce-mobile-snap-row flex gap-4 overflow-x-auto py-8 md:grid md:grid-cols-3 md:overflow-visible xl:py-10">
          {steps.map(({ icon: Icon, title, detail }, index) => (
            <InteractiveSurface
              as="article"
              key={title}
              className={`ce-reveal ce-reveal-delay-${Math.min(index + 1, 3)} min-w-[78vw] snap-start rounded-2xl border border-white/10 bg-white/[0.035] p-5 transition hover:-translate-y-1 hover:border-cyan-300/35 hover:bg-white/[0.055] md:min-w-0`}
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

      <section className="border-b border-white/10 bg-transparent">
        <div className="ce-shell ce-page">
          <div className="grid gap-8 xl:grid-cols-[420px_minmax(0,1fr)] xl:items-start">
            <div className="ce-reveal">
              <p className="text-sm font-black text-cyan-200">
                {pick("Verdict pe înțelesul tău", "Verdicts made simple")}
              </p>
              <h2 className="mt-3 text-4xl font-black leading-tight md:text-5xl">
                {pick(
                  "Nu primești doar un scor. Primești o alegere clară.",
                  "You do not just get a score. You get a clear choice."
                )}
              </h2>
              <p className="mt-4 leading-8 text-gray-300">
                {pick(
                  "Rezultatul arată produsul scanat, motivul verdictului și o alternativă apropiată din aceeași familie de produse.",
                  "The result shows the scanned product, the reason behind the verdict and a close alternative from the same product family."
                )}
              </p>
            </div>

            <InteractiveSurface className="ce-reveal ce-reveal-delay-1 rounded-3xl border border-white/10 bg-white/[0.04] p-4 shadow-2xl backdrop-blur md:p-5">
              <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr] lg:items-stretch">
                <article className="rounded-2xl border border-rose-300/25 bg-rose-300/10 p-4">
                  <p className="text-xs font-black uppercase text-rose-100">
                    {pick("Produs scanat", "Scanned product")}
                  </p>
                  <div className="mt-4 flex gap-4">
                    <div className="relative h-28 w-28 shrink-0 overflow-hidden rounded-2xl bg-white">
                      <Image
                        src="/products/baton-ovaz.jpg"
                        alt={pick("Snack dulce scanat", "Scanned sweet snack")}
                        fill
                        sizes="112px"
                        className="object-cover"
                      />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-2xl font-black">{pick("Snack dulce", "Sweet snack")}</h3>
                      <p className="mt-2 text-sm leading-6 text-gray-300">
                        {pick(
                          "Zahăr ridicat și scor slab pentru categoria lui.",
                          "High sugar and a weak score for its category."
                        )}
                      </p>
                      <div className="mt-3 inline-flex rounded-full bg-rose-200 px-3 py-1 text-sm font-black text-black">
                        3.4/10
                      </div>
                    </div>
                  </div>
                </article>

                <div className="flex items-center justify-center">
                  <span className="flex h-12 w-12 items-center justify-center rounded-full border border-cyan-300/25 bg-cyan-300/10 text-cyan-100 shadow-[0_0_26px_rgba(103,232,249,.18)]">
                    <ArrowRight size={22} />
                  </span>
                </div>

                <article className="rounded-2xl border border-cyan-300/25 bg-cyan-300/10 p-4">
                  <p className="text-xs font-black uppercase text-cyan-100">
                    {pick("Alternativă recomandată", "Recommended alternative")}
                  </p>
                  <div className="mt-4 flex gap-4">
                    <div className="relative h-28 w-28 shrink-0 overflow-hidden rounded-2xl bg-white">
                      <Image
                        src="/products/baton-proteic.jpg"
                        alt={pick("Baton proteic recomandat", "Recommended protein bar")}
                        fill
                        sizes="112px"
                        className="object-contain p-2"
                      />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-2xl font-black">{pick("Baton proteic", "Protein bar")}</h3>
                      <p className="mt-2 text-sm leading-6 text-gray-300">
                        {pick(
                          "Mai multă proteină și profil mai echilibrat pentru aceeași nevoie.",
                          "More protein and a more balanced profile for the same need."
                        )}
                      </p>
                      <div className="mt-3 inline-flex rounded-full bg-cyan-200 px-3 py-1 text-sm font-black text-black">
                        8.6/10
                      </div>
                    </div>
                  </div>
                </article>
              </div>
            </InteractiveSurface>
          </div>

          <div className="ce-mobile-snap-row mt-5 flex gap-4 overflow-x-auto pb-2 lg:grid lg:grid-cols-3 lg:overflow-visible lg:pb-0">
              {verdictCards.map(({ icon: Icon, image, tone, badge, title, score, detail, points }, index) => (
                <InteractiveSurface
                  as="article"
                  key={title}
                  className={`ce-reveal ce-reveal-delay-${Math.min(index + 1, 3)} min-w-[82vw] snap-start overflow-hidden rounded-2xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur transition hover:-translate-y-1 hover:border-cyan-300/35 hover:bg-white/[0.065] lg:min-w-0`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-black ${tone}`}>
                      <Icon size={15} />
                      {badge}
                    </span>
                    <span className="rounded-full bg-white px-3 py-1 text-sm font-black text-black">
                      {score}/10
                    </span>
                  </div>
                  <div className="mt-5 flex gap-4">
                    <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-2xl bg-white">
                      <Image
                        src={image}
                        alt={title}
                        fill
                        sizes="96px"
                        className="object-contain p-2"
                      />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-xl font-black">{title}</h3>
                      <p className="mt-2 text-sm leading-6 text-gray-300">{detail}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {points.map((point) => (
                      <span
                        key={point}
                        className="rounded-full border border-white/10 bg-black/25 px-3 py-1 text-xs font-bold text-gray-200"
                      >
                        {point}
                      </span>
                    ))}
                  </div>
                </InteractiveSurface>
              ))}
          </div>
        </div>
      </section>

      <section className="bg-[#070a0e]">
        <div className="ce-shell ce-page">
          <div className="grid gap-8 xl:grid-cols-[420px_minmax(0,1fr)] xl:items-start">
            <div>
              <p className="text-sm font-black text-cyan-200">
                {pick("La raft, fără ghicit", "At the shelf, without guessing")}
              </p>
              <h2 className="mt-3 text-4xl font-black leading-tight md:text-5xl">
                {pick(
                  "Tot ce ai nevoie în fața raftului.",
                  "Everything you need in front of the shelf."
                )}
              </h2>
              <p className="mt-4 leading-8 text-gray-300">
                {pick(
                  "Aplicația este gândită pentru momentele în care vrei un răspuns rapid: merită produsul sau există o variantă mai bună?",
                  "The app is built for the moment when you need a quick answer: is this product worth it or is there a better option?"
                )}
              </p>
            </div>

            <div className="ce-mobile-snap-row flex gap-4 overflow-x-auto pb-2 md:grid md:grid-cols-3 md:overflow-visible md:pb-0">
              {capabilities.map(({ icon: Icon, label, detail }, index) => (
                <InteractiveSurface
                  as="article"
                  key={label}
                  className={`ce-reveal ce-reveal-delay-${Math.min(index + 1, 3)} min-w-[78vw] snap-start rounded-2xl border border-white/10 bg-white/[0.035] p-5 shadow-xl backdrop-blur transition hover:-translate-y-1 hover:border-cyan-300/35 hover:bg-white/[0.055] md:min-w-0`}
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
                {pick("Pentru următoarea cumpărătură", "For your next shop")}
              </p>
              <h2 className="mt-2 text-2xl font-black">
                {pick(
                  "Scanează codul și verifică produsul înainte să îl pui în coș.",
                  "Scan the barcode and check the product before it goes in your cart."
                )}
              </h2>
            </div>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row md:mt-0">
              <Link
                href={isAuthenticated ? "/dashboard" : "/register"}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
              >
                {isAuthenticated ? pick("Mergi la dashboard", "Go to dashboard") : pick("Creează cont", "Create account")}
                <ArrowRight size={18} />
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-yellow-300/35 bg-yellow-300/10 px-5 py-3 font-black text-yellow-100 hover:bg-yellow-300/20"
              >
                <Crown size={18} />
                {pick("Compară planurile", "Compare plans")}
              </Link>
            </div>
          </InteractiveSurface>
        </div>
      </section>

    </main>
  );
}

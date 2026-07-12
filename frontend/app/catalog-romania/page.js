"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Barcode,
  CheckCircle2,
  Clock3,
  Database,
  Gift,
  Medal,
  PackageCheck,
  PlusCircle,
  SearchX,
  Share2,
  ShieldCheck,
  Sparkles,
  Store,
  TrendingUp,
  Users,
} from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";
import { API_URL } from "../config";
import { SEO_ALTERNATIVE_GUIDES, SEO_CATEGORIES, SEO_PRODUCTS, SEO_STORES } from "./seo-data";

const fallbackStats = {
  products: 0,
  barcodeCoverage: 0,
  nutritionCoverage: 0,
  imageCoverage: 0,
  uncategorizedRate: 0,
  approvedSubmissions: 0,
  pendingSubmissions: 0,
  contributors: 0,
  searchesLast30Days: 0,
  missingProductsLast30Days: 0,
  categories: [],
  stores: [],
  missingByStore: [],
  topContributors: [],
  recentCommunityProducts: [],
};

function StatTile({ icon: Icon, label, value, detail, tone = "emerald" }) {
  const toneClasses = {
    emerald: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100",
    cyan: "border-cyan-300/25 bg-cyan-300/10 text-cyan-100",
    amber: "border-amber-300/25 bg-amber-300/10 text-amber-100",
    rose: "border-rose-300/25 bg-rose-300/10 text-rose-100",
  };

  return (
    <article className="min-w-[11.5rem] snap-start rounded-lg border border-white/10 bg-white/[0.045] p-4 shadow-xl shadow-black/15 sm:min-w-0">
      <div
        className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border ${
          toneClasses[tone] || toneClasses.emerald
        }`}
      >
        <Icon size={20} />
      </div>
      <p className="text-2xl font-black text-white">{value}</p>
      <p className="mt-1 text-sm font-bold text-gray-200">{label}</p>
      {detail && <p className="mt-2 text-xs leading-relaxed text-gray-400">{detail}</p>}
    </article>
  );
}

function ProgressRow({ label, value, total, detail }) {
  const percent = total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="min-w-0 truncate font-bold text-gray-100">{label}</span>
        <span className="shrink-0 text-xs font-black text-cyan-100">{detail || `${percent}%`}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-emerald-300 via-cyan-300 to-amber-200"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function EmptyList({ text }) {
  return (
    <div className="rounded-lg border border-dashed border-white/15 bg-white/[0.03] p-5 text-sm text-gray-300">
      {text}
    </div>
  );
}

export default function CatalogRomaniaPage() {
  const { locale, pick } = useLocale();
  const [stats, setStats] = useState(fallbackStats);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const formatter = useMemo(
    () => new Intl.NumberFormat(locale === "en" ? "en-US" : "ro-RO"),
    [locale]
  );

  function formatNumber(value) {
    return formatter.format(Number(value || 0));
  }

  function formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
  }

  useEffect(() => {
    let isMounted = true;

    async function loadStats() {
      try {
        setLoading(true);
        setLoadError("");
        const response = await fetch(`${API_URL}/catalog/romania/stats`, {
          headers: { Accept: "application/json" },
        });

        if (!response.ok) {
          throw new Error("catalog_stats_failed");
        }

        const data = await response.json();
        if (isMounted) setStats({ ...fallbackStats, ...data });
      } catch {
        if (isMounted) {
          setStats(fallbackStats);
          setLoadError(
            pick(
              "Nu am putut încărca statistica live. Pagina rămâne disponibilă.",
              "Live catalog stats could not be loaded. The page is still available."
            )
          );
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    void loadStats();

    return () => {
      isMounted = false;
    };
  }, [pick]);

  const maxCategoryCount = Math.max(
    1,
    ...stats.categories.map((item) => Number(item.count || 0))
  );
  const maxStoreCount = Math.max(1, ...stats.stores.map((item) => Number(item.count || 0)));

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel={pick("Scanează", "Scan")} />

      <section className="ce-shell ce-page space-y-8 pb-28">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(20rem,0.85fr)] lg:items-stretch">
          <div className="flex flex-col justify-center py-2">
            <div className="mb-4 inline-flex w-fit items-center gap-2 rounded-lg border border-emerald-300/25 bg-emerald-300/10 px-3 py-2 text-xs font-black uppercase tracking-[0.16em] text-emerald-100">
              <Database size={15} />
              {pick("Catalog România", "Romania catalog")}
            </div>
            <h1 className="max-w-3xl text-4xl font-black leading-tight text-white md:text-6xl">
              {pick("Catalogul care crește cu fiecare scanare.", "A catalog that grows with every scan.")}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-gray-300 md:text-lg">
              {pick(
                "Aici vezi cât de mare este catalogul Ce aleg?, unde lipsesc produse și cum ajută comunitatea să acopere magazinele din România.",
                "See how large the Ce aleg? catalog is, where products are missing, and how the community helps cover Romanian stores."
              )}
            </p>
            <div className="mt-6 flex snap-x gap-3 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible">
              <Link
                href="/store"
                className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
              >
                <Store size={18} />
                {pick("Alege magazin", "Pick store")}
              </Link>
              <Link
                href="/submit-product"
                className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-300/10 px-4 py-3 text-sm font-black text-emerald-100 transition hover:-translate-y-0.5 hover:bg-emerald-300/20"
              >
                <PlusCircle size={18} />
                {pick("Adaugă produs", "Add product")}
              </Link>
              <Link
                href="/missions"
                className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-lg border border-amber-300/35 bg-amber-300/10 px-4 py-3 text-sm font-black text-amber-100 transition hover:-translate-y-0.5 hover:bg-amber-300/20"
              >
                <Gift size={18} />
                {pick("Vezi misiuni", "View missions")}
              </Link>
            </div>
          </div>

          <InteractiveSurface className="rounded-lg border border-white/10 bg-[#111923]/82 p-5 shadow-2xl shadow-black/25 backdrop-blur">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-bold text-gray-400">
                  {pick("Acoperire catalog", "Catalog coverage")}
                </p>
                <p className="mt-1 text-3xl font-black text-white">
                  {formatNumber(stats.products)}
                </p>
                <p className="mt-1 text-sm text-gray-400">
                  {pick("produse în baza activă", "products in the active database")}
                </p>
              </div>
              <div className="rounded-lg border border-cyan-300/25 bg-cyan-300/10 p-3 text-cyan-100">
                <TrendingUp size={24} />
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <ProgressRow
                label={pick("Cu cod de bare", "With barcode")}
                value={stats.withBarcode}
                total={stats.products}
                detail={formatPercent(stats.barcodeCoverage)}
              />
              <ProgressRow
                label={pick("Cu nutriție", "With nutrition")}
                value={stats.withNutrition}
                total={stats.products}
                detail={formatPercent(stats.nutritionCoverage)}
              />
              <ProgressRow
                label={pick("Cu imagine", "With image")}
                value={stats.withImage}
                total={stats.products}
                detail={formatPercent(stats.imageCoverage)}
              />
            </div>

            <div className="mt-6 rounded-lg border border-white/10 bg-white/[0.04] p-4">
              <div className="flex items-center gap-2 text-sm font-black text-emerald-100">
                <ShieldCheck size={18} />
                {pick("Date publice, fără emailuri", "Public stats, no emails")}
              </div>
              <p className="mt-2 text-sm leading-6 text-gray-300">
                {pick(
                  "Topul contributorilor afișează doar prenume sau un alias sigur.",
                  "Contributor rankings show only first names or a safe alias."
                )}
              </p>
            </div>
          </InteractiveSurface>
        </div>

        {loadError && (
          <div className="rounded-lg border border-amber-300/25 bg-amber-300/10 p-4 text-sm font-bold text-amber-100">
            {loadError}
          </div>
        )}

        <div className="grid snap-x auto-cols-[minmax(11.5rem,1fr)] grid-flow-col gap-3 overflow-x-auto pb-1 sm:grid-flow-row sm:grid-cols-2 sm:overflow-visible lg:grid-cols-5">
          <StatTile
            icon={PackageCheck}
            label={pick("Produse", "Products")}
            value={loading ? "..." : formatNumber(stats.products)}
            detail={pick("în catalogul curent", "in the current catalog")}
          />
          <StatTile
            icon={Barcode}
            label={pick("Coduri de bare", "Barcodes")}
            value={loading ? "..." : formatPercent(stats.barcodeCoverage)}
            detail={pick("gata pentru scanare", "ready for scanning")}
            tone="cyan"
          />
          <StatTile
            icon={CheckCircle2}
            label={pick("Contribuții aprobate", "Approved contributions")}
            value={loading ? "..." : formatNumber(stats.approvedSubmissions)}
            detail={pick("produse validate", "validated products")}
          />
          <StatTile
            icon={Users}
            label={pick("Contributori", "Contributors")}
            value={loading ? "..." : formatNumber(stats.contributors)}
            detail={pick("care au ajutat catalogul", "who helped the catalog")}
            tone="amber"
          />
          <StatTile
            icon={SearchX}
            label={pick("Lipsuri 30 zile", "30-day misses")}
            value={loading ? "..." : formatNumber(stats.missingProductsLast30Days)}
            detail={pick("scanări/căutări negăsite", "missing scans/searches")}
            tone="rose"
          />
        </div>

        <section className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15">
          <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-2xl font-black text-white">
                {pick("Pagini publice pentru trafic gratuit", "Public pages for free traffic")}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-400">
                {pick(
                  "Le poti distribui in grupuri sau lasa pentru Google: magazine si categorii unde explicam ce se poate scana si cum creste catalogul.",
                  "Share them in groups or let Google index them: stores and categories that explain what can be scanned and how the catalog grows."
                )}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/catalog-romania/magazine"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-300/10 px-4 py-3 text-sm font-black text-emerald-100 hover:bg-emerald-300/20"
              >
                <Store size={17} />
                {pick("Magazine", "Stores")}
              </Link>
              <Link
                href="/catalog-romania/categorii"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-cyan-300/35 bg-cyan-300/10 px-4 py-3 text-sm font-black text-cyan-100 hover:bg-cyan-300/20"
              >
                <Database size={17} />
                {pick("Categorii", "Categories")}
              </Link>
              <Link
                href="/catalog-romania/produse"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/[0.04] px-4 py-3 text-sm font-black text-white hover:bg-white/[0.08]"
              >
                <PackageCheck size={17} />
                {pick("Produse", "Products")}
              </Link>
              <Link
                href="/catalog-romania/alternative"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-amber-300/35 bg-amber-300/10 px-4 py-3 text-sm font-black text-amber-100 hover:bg-amber-300/20"
              >
                <Sparkles size={17} />
                {pick("Alternative", "Alternatives")}
              </Link>
              <Link
                href="/promovare-gratis"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/[0.04] px-4 py-3 text-sm font-black text-white hover:bg-white/[0.08]"
              >
                <Share2 size={17} />
                {pick("Promovare", "Promote")}
              </Link>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-4">
            <div>
              <p className="mb-3 text-sm font-black uppercase tracking-[0.14em] text-emerald-100">
                {pick("Magazine", "Stores")}
              </p>
              <div className="grid gap-2">
                {SEO_STORES.slice(0, 4).map((store) => (
                  <Link
                    key={store.slug}
                    href={`/catalog-romania/magazine/${store.slug}`}
                    className="rounded-lg border border-white/10 bg-white/[0.035] p-3 text-sm font-black text-white transition hover:-translate-y-0.5 hover:border-emerald-300/35 hover:bg-white/[0.065]"
                  >
                    {store.name}
                    <span className="mt-1 block text-xs font-semibold leading-5 text-gray-400">
                      {store.shopperIntent}
                    </span>
                  </Link>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-3 text-sm font-black uppercase tracking-[0.14em] text-cyan-100">
                {pick("Categorii", "Categories")}
              </p>
              <div className="grid gap-2">
                {SEO_CATEGORIES.slice(0, 4).map((category) => (
                  <Link
                    key={category.slug}
                    href={`/catalog-romania/categorii/${category.slug}`}
                    className="rounded-lg border border-white/10 bg-white/[0.035] p-3 text-sm font-black text-white transition hover:-translate-y-0.5 hover:border-cyan-300/35 hover:bg-white/[0.065]"
                  >
                    {category.name}
                    <span className="mt-1 block text-xs font-semibold leading-5 text-gray-400">
                      {category.compareSignals.slice(0, 3).join(" / ")}
                    </span>
                  </Link>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-3 text-sm font-black uppercase tracking-[0.14em] text-white">
                {pick("Produse", "Products")}
              </p>
              <div className="grid gap-2">
                {SEO_PRODUCTS.slice(0, 4).map((product) => (
                  <Link
                    key={product.slug}
                    href={`/catalog-romania/produse/${product.slug}`}
                    className="rounded-lg border border-white/10 bg-white/[0.035] p-3 text-sm font-black text-white transition hover:-translate-y-0.5 hover:border-white/30 hover:bg-white/[0.065]"
                  >
                    {product.name}
                    <span className="mt-1 block text-xs font-semibold leading-5 text-gray-400">
                      {product.score}/10 / {product.verdict}
                    </span>
                  </Link>
                ))}
              </div>
            </div>

            <div>
              <p className="mb-3 text-sm font-black uppercase tracking-[0.14em] text-amber-100">
                {pick("Alternative", "Alternatives")}
              </p>
              <div className="grid gap-2">
                {SEO_ALTERNATIVE_GUIDES.slice(0, 4).map((guide) => (
                  <Link
                    key={guide.slug}
                    href={`/catalog-romania/alternative/${guide.slug}`}
                    className="rounded-lg border border-white/10 bg-white/[0.035] p-3 text-sm font-black text-white transition hover:-translate-y-0.5 hover:border-amber-300/35 hover:bg-white/[0.065]"
                  >
                    {guide.title}
                    <span className="mt-1 block text-xs font-semibold leading-5 text-gray-400">
                      {guide.checks.slice(0, 3).join(" / ")}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <section className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-black text-white">
                  {pick("Ce avem deja", "What we already have")}
                </h2>
                <p className="mt-1 text-sm text-gray-400">
                  {pick("Cele mai populate categorii.", "The most populated categories.")}
                </p>
              </div>
              <Database className="text-emerald-200" size={22} />
            </div>
            <div className="space-y-4">
              {stats.categories.length ? (
                stats.categories.map((item) => (
                  <ProgressRow
                    key={item.name}
                    label={item.name}
                    value={Number(item.count || 0)}
                    total={maxCategoryCount}
                    detail={formatNumber(item.count)}
                  />
                ))
              ) : (
                <EmptyList text={pick("Nu există încă statistici pe categorii.", "No category stats yet.")} />
              )}
            </div>
          </section>

          <section className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-black text-white">
                  {pick("Magazine acoperite", "Covered stores")}
                </h2>
                <p className="mt-1 text-sm text-gray-400">
                  {pick("Unde există cele mai multe produse.", "Where most products are available.")}
                </p>
              </div>
              <Store className="text-cyan-200" size={22} />
            </div>
            <div className="space-y-4">
              {stats.stores.length ? (
                stats.stores.map((item) => (
                  <ProgressRow
                    key={item.name}
                    label={item.name}
                    value={Number(item.count || 0)}
                    total={maxStoreCount}
                    detail={formatNumber(item.count)}
                  />
                ))
              ) : (
                <EmptyList text={pick("Nu există încă statistici pe magazine.", "No store stats yet.")} />
              )}
            </div>
          </section>
        </div>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <section className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-black text-white">
                  {pick("Unde lipsesc produse", "Where products are missing")}
                </h2>
                <p className="mt-1 text-sm text-gray-400">
                  {pick("Semnale din ultimele 30 de zile.", "Signals from the last 30 days.")}
                </p>
              </div>
              <SearchX className="text-rose-200" size={22} />
            </div>
            <div className="space-y-3">
              {stats.missingByStore.length ? (
                stats.missingByStore.map((item) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-black text-white">{item.name}</p>
                      <p className="mt-1 text-xs text-gray-400">
                        {pick("produs negăsit", "missing product")}
                      </p>
                    </div>
                    <span className="rounded-lg bg-rose-300/12 px-3 py-1 text-sm font-black text-rose-100">
                      {formatNumber(item.count)}
                    </span>
                  </div>
                ))
              ) : (
                <EmptyList text={pick("Momentan nu sunt lipsuri grupate pe magazin.", "No store misses grouped yet.")} />
              )}
            </div>
          </section>

          <section className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-black text-white">
                  {pick("Comunitatea", "Community")}
                </h2>
                <p className="mt-1 text-sm text-gray-400">
                  {pick("Produse aprobate și contribuitori activi.", "Approved products and active contributors.")}
                </p>
              </div>
              <Medal className="text-amber-200" size={22} />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-3">
                {stats.topContributors.length ? (
                  stats.topContributors.map((item) => (
                    <div
                      key={`${item.rank}-${item.name}`}
                      className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-3"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-300/15 text-sm font-black text-amber-100">
                        #{item.rank}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-black text-white">{item.name}</p>
                        <p className="text-xs text-gray-400">
                          {formatNumber(item.approvedSubmissions)} {pick("aprobate", "approved")}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyList text={pick("Topul apare după primele aprobări.", "Ranking appears after first approvals.")} />
                )}
              </div>

              <div className="space-y-3">
                {stats.recentCommunityProducts.length ? (
                  stats.recentCommunityProducts.map((item) => (
                    <div
                      key={`${item.name}-${item.createdAt}`}
                      className="rounded-lg border border-white/10 bg-white/[0.035] p-3"
                    >
                      <p className="line-clamp-2 text-sm font-black text-white">{item.name}</p>
                      <p className="mt-1 text-xs text-gray-400">
                        {[item.brand, item.store, item.category].filter(Boolean).join(" · ")}
                      </p>
                    </div>
                  ))
                ) : (
                  <EmptyList text={pick("Produsele recente apar după aprobare.", "Recent products appear after approval.")} />
                )}
              </div>
            </div>
          </section>
        </div>

        <section className="grid gap-4 rounded-lg border border-emerald-300/20 bg-emerald-300/10 p-5 sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <div className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.14em] text-emerald-100">
              <Clock3 size={17} />
              {pick("Următorul pas", "Next step")}
            </div>
            <h2 className="mt-2 text-2xl font-black text-white">
              {pick("Când scanezi un produs lipsă, îl poți trimite la verificare.", "When a scanned product is missing, you can submit it for review.")}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-300">
              {pick(
                "După aprobare primești CeCoins, iar catalogul devine mai util pentru toți utilizatorii.",
                "After approval you receive CeCoins, and the catalog becomes more useful for everyone."
              )}
            </p>
          </div>
          <Link
            href="/barcode-scan"
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
          >
            {pick("Începe scanarea", "Start scanning")}
            <ArrowRight size={18} />
          </Link>
        </section>
      </section>
    </main>
  );
}

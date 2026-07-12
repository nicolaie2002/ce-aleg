import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Barcode,
  CheckCircle2,
  Database,
  Search,
  Sparkles,
  Store,
  UploadCloud,
} from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import { CATALOG_SEO_SITE_URL } from "./seo-data";

export function JsonLd({ data }) {
  return (
    <script
      type="application/ld+json"
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

export function buildBreadcrumbJsonLd(items) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: `${CATALOG_SEO_SITE_URL}${item.href}`,
    })),
  };
}

export function CatalogSeoLayout({ eyebrow, title, description, image, imageAlt, children }) {
  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/barcode-scan" actionLabel="Scaneaza" />
      <section className="ce-shell ce-page space-y-8 pb-28">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.12fr)_minmax(19rem,0.88fr)] lg:items-center">
          <div>
            <Link
              href="/catalog-romania"
              className="mb-5 inline-flex w-fit items-center gap-2 rounded-lg border border-emerald-300/25 bg-emerald-300/10 px-3 py-2 text-xs font-black uppercase text-emerald-100 transition hover:bg-emerald-300/18"
            >
              <Database size={15} />
              Catalog Romania
            </Link>
            <p className="text-sm font-black uppercase text-cyan-100">{eyebrow}</p>
            <h1 className="mt-3 max-w-4xl text-4xl font-black leading-tight md:text-6xl">
              {title}
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-gray-300 md:text-lg">
              {description}
            </p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/barcode-scan"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
              >
                <Barcode size={18} />
                Scaneaza un produs
              </Link>
              <Link
                href="/submit-product"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-300/10 px-5 py-3 text-sm font-black text-emerald-100 transition hover:-translate-y-0.5 hover:bg-emerald-300/20"
              >
                <UploadCloud size={18} />
                Adauga produs lipsa
              </Link>
            </div>
          </div>

          <div className="relative min-h-[17rem] overflow-hidden rounded-lg border border-white/10 bg-white/[0.04] shadow-2xl shadow-black/25">
            <Image
              src={image}
              alt={imageAlt}
              fill
              sizes="(min-width: 1024px) 38vw, 100vw"
              className="object-contain p-8"
              priority
              unoptimized
            />
            <div className="absolute inset-x-0 bottom-0 border-t border-white/10 bg-black/45 p-4 backdrop-blur">
              <p className="flex items-center gap-2 text-sm font-black text-cyan-100">
                <Sparkles size={16} />
                Scanare cod de bare, alternative si catalog construit de comunitate.
              </p>
            </div>
          </div>
        </div>

        {children}
      </section>
    </main>
  );
}

export function SeoSection({ title, description, icon: Icon = Search, children }) {
  return (
    <section className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-white">{title}</h2>
          {description ? (
            <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-400">{description}</p>
          ) : null}
        </div>
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-cyan-300/25 bg-cyan-300/10 text-cyan-100">
          <Icon size={20} />
        </span>
      </div>
      {children}
    </section>
  );
}

export function PillGrid({ items, tone = "cyan" }) {
  const toneClass =
    tone === "emerald"
      ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-100"
      : "border-cyan-300/25 bg-cyan-300/10 text-cyan-100";

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span key={item} className={`rounded-lg border px-3 py-2 text-sm font-bold ${toneClass}`}>
          {item}
        </span>
      ))}
    </div>
  );
}

export function StepList({ items }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {items.map((item, index) => (
        <article key={item} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-black text-black">
            {index + 1}
          </span>
          <p className="mt-4 text-sm font-bold leading-6 text-gray-200">{item}</p>
        </article>
      ))}
    </div>
  );
}

export function CategoryCard({ category }) {
  return (
    <Link
      href={`/catalog-romania/categorii/${category.slug}`}
      className="group grid min-h-[14rem] overflow-hidden rounded-lg border border-white/10 bg-white/[0.04] transition hover:-translate-y-0.5 hover:border-cyan-300/40 hover:bg-white/[0.07]"
    >
      <div className="relative min-h-32 bg-white">
        <Image
          src={category.image}
          alt={category.name}
          fill
          sizes="(min-width: 1024px) 22vw, 90vw"
          className="object-contain p-5"
          loading="lazy"
          unoptimized
        />
      </div>
      <div className="p-4">
        <h3 className="text-lg font-black text-white">{category.name}</h3>
        <p className="mt-2 line-clamp-3 text-sm leading-6 text-gray-400">{category.intro}</p>
        <span className="mt-4 inline-flex items-center gap-2 text-sm font-black text-cyan-100">
          Vezi ghidul
          <ArrowRight size={16} />
        </span>
      </div>
    </Link>
  );
}

export function StoreCard({ store }) {
  return (
    <Link
      href={`/catalog-romania/magazine/${store.slug}`}
      className="group grid min-h-[14rem] overflow-hidden rounded-lg border border-white/10 bg-white/[0.04] transition hover:-translate-y-0.5 hover:border-emerald-300/40 hover:bg-white/[0.07]"
    >
      <div className="relative min-h-32 bg-white">
        <Image
          src={store.logo}
          alt={`${store.name} logo`}
          fill
          sizes="(min-width: 1024px) 22vw, 90vw"
          className="object-contain p-6"
          loading="lazy"
          unoptimized
        />
      </div>
      <div className="p-4">
        <h3 className="text-lg font-black text-white">{store.name}</h3>
        <p className="mt-2 line-clamp-3 text-sm leading-6 text-gray-400">{store.tagline}</p>
        <span className="mt-4 inline-flex items-center gap-2 text-sm font-black text-emerald-100">
          Vezi pagina magazinului
          <ArrowRight size={16} />
        </span>
      </div>
    </Link>
  );
}

export function SeoCtaBand() {
  return (
    <section className="grid gap-4 rounded-lg border border-emerald-300/20 bg-emerald-300/10 p-5 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p className="flex items-center gap-2 text-sm font-black uppercase text-emerald-100">
          <CheckCircle2 size={17} />
          Catalogul creste gratis
        </p>
        <h2 className="mt-2 text-2xl font-black text-white">
          Produs negasit? Trimite-l la verificare si ajuta catalogul pentru Romania.
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-300">
          Nu avem nevoie sa asteptam liste de la retaileri. Produsele reale scanate de utilizatori fac aplicatia mai utila pentru toti.
        </p>
      </div>
      <Link
        href="/submit-product"
        className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
      >
        Trimite produs
        <ArrowRight size={18} />
      </Link>
    </section>
  );
}

export function StoreCategoryLinks({ categories }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {categories.map((category) => (
        <Link
          key={category.slug}
          href={`/catalog-romania/categorii/${category.slug}`}
          className="rounded-lg border border-white/10 bg-white/[0.04] p-4 transition hover:-translate-y-0.5 hover:border-cyan-300/35 hover:bg-white/[0.065]"
        >
          <p className="flex items-center gap-2 text-sm font-black text-cyan-100">
            <Database size={16} />
            {category.name}
          </p>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-gray-400">{category.advice}</p>
        </Link>
      ))}
    </div>
  );
}

export function CategoryStoreLinks({ stores }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {stores.map((store) => (
        <Link
          key={store.slug}
          href={`/catalog-romania/magazine/${store.slug}`}
          className="rounded-lg border border-white/10 bg-white/[0.04] p-4 transition hover:-translate-y-0.5 hover:border-emerald-300/35 hover:bg-white/[0.065]"
        >
          <p className="flex items-center gap-2 text-sm font-black text-emerald-100">
            <Store size={16} />
            {store.name}
          </p>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-gray-400">{store.shopperIntent}</p>
        </Link>
      ))}
    </div>
  );
}

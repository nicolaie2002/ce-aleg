import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Barcode,
  CheckCircle2,
  Megaphone,
  MessageCircle,
  Search,
  Share2,
  ShieldCheck,
  ShoppingBag,
  Users,
} from "lucide-react";
import { AppHeader } from "../components/AppHeader";
import OrganicPromotionKit from "./OrganicPromotionKit";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop").replace(/\/$/, "");

export const metadata = {
  title: "Promovare gratis pentru Ce aleg? | Kit organic",
  description:
    "Texte gata de copiat pentru promovare organica Ce aleg?: Facebook, WhatsApp, TikTok, comentarii si linkuri publice pentru catalogul Romania.",
  alternates: {
    canonical: `${SITE_URL}/promovare-gratis`,
  },
  openGraph: {
    title: "Promovare gratis pentru Ce aleg?",
    description:
      "Kit organic cu texte gata de copiat, linkuri publice si reguli simple pentru a atrage utilizatori fara reclame platite.",
    url: `${SITE_URL}/promovare-gratis`,
    siteName: "Ce aleg?",
    type: "website",
    images: [
      {
        url: `${SITE_URL}/opengraph-image.png`,
        width: 1200,
        height: 630,
        alt: "Ce aleg?",
      },
    ],
  },
};

const channels = [
  {
    title: "Grupuri Facebook",
    text: "Grupuri locale, parinti, cumparaturi, nutritie, fitness si comunitati de cartier.",
    icon: Users,
    tone: "emerald",
  },
  {
    title: "WhatsApp",
    text: "Mesaj scurt pentru prieteni care merg des la cumparaturi si pot testa rapid scanarea.",
    icon: MessageCircle,
    tone: "cyan",
  },
  {
    title: "Clipuri scurte",
    text: "Demo real la raft: scanezi, vezi rezultatul, arati ce se intampla cand produsul lipseste.",
    icon: Share2,
    tone: "amber",
  },
  {
    title: "Comentarii utile",
    text: "Raspunsuri naturale acolo unde oamenii intreaba despre produse, etichete sau alternative.",
    icon: Search,
    tone: "white",
  },
];

const rules = [
  "Posteaza doar unde tema grupului are legatura cu produsul, cumparaturile sau sanatatea.",
  "Spune clar ca aplicatia este in crestere si cauti feedback real.",
  "Nu promite ca produsul exista deja in catalog. Daca lipseste, omul il poate trimite la verificare.",
  "Nu repeta acelasi mesaj identic peste tot. Schimba prima fraza dupa context.",
];

function toneClass(tone) {
  const map = {
    emerald: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100",
    cyan: "border-cyan-300/25 bg-cyan-300/10 text-cyan-100",
    amber: "border-amber-300/25 bg-amber-300/10 text-amber-100",
    white: "border-white/15 bg-white/[0.05] text-white",
  };

  return map[tone] || map.emerald;
}

function JsonLd({ data }) {
  return (
    <script
      type="application/ld+json"
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

export default function PromovareGratisPage() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: "Promovare gratis pentru Ce aleg?",
    description: metadata.description,
    url: `${SITE_URL}/promovare-gratis`,
    isPartOf: {
      "@type": "WebSite",
      name: "Ce aleg?",
      url: SITE_URL,
    },
  };

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <JsonLd data={jsonLd} />
      <AppHeader actionHref="/barcode-scan" actionLabel="Scaneaza" />

      <section className="ce-shell ce-page space-y-8 pb-28">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.04fr)_minmax(19rem,0.96fr)] lg:items-center">
          <div>
            <Link
              href="/catalog-romania"
              className="mb-5 inline-flex w-fit items-center gap-2 rounded-lg border border-emerald-300/25 bg-emerald-300/10 px-3 py-2 text-xs font-black uppercase tracking-[0.14em] text-emerald-100 transition hover:bg-emerald-300/18"
            >
              <ShoppingBag size={15} />
              Catalog Romania
            </Link>
            <h1 className="max-w-4xl text-4xl font-black leading-tight text-white md:text-6xl">
              Promovare gratis pentru Ce aleg?
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-gray-300 md:text-lg">
              Kit simplu pentru crestere fara reclame platite: texte gata de copiat, linkuri bune de trimis si reguli ca mesajele sa para naturale, nu agresive.
            </p>

            <div className="mt-7 flex snap-x gap-3 overflow-x-auto pb-1 sm:flex-wrap sm:overflow-visible">
              <a
                href="#texte"
                className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
              >
                <Megaphone size={18} />
                Vezi textele
              </a>
              <Link
                href="/catalog-romania"
                className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-lg border border-cyan-300/35 bg-cyan-300/10 px-5 py-3 text-sm font-black text-cyan-100 transition hover:-translate-y-0.5 hover:bg-cyan-300/20"
              >
                <Barcode size={18} />
                Link catalog
              </Link>
              <Link
                href="/submit-product"
                className="inline-flex min-h-12 shrink-0 items-center justify-center gap-2 rounded-lg border border-emerald-300/35 bg-emerald-300/10 px-5 py-3 text-sm font-black text-emerald-100 transition hover:-translate-y-0.5 hover:bg-emerald-300/20"
              >
                Produs lipsa
                <ArrowRight size={18} />
              </Link>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-white/10 bg-[#101820]/82 shadow-2xl shadow-black/25">
            <div className="relative min-h-[16rem] bg-white">
              <Image
                src="/brand/ce-aleg-logo.png"
                alt="Ce aleg?"
                fill
                sizes="(min-width: 1024px) 38vw, 100vw"
                className="object-contain p-8"
                priority
                unoptimized
              />
            </div>
            <div className="grid gap-3 p-4 sm:grid-cols-3">
              {[
                ["0 lei", "buget minim"],
                ["5 texte", "gata de copiat"],
                ["4 linkuri", "usor de distribuit"],
              ].map(([value, label]) => (
                <div key={value} className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
                  <p className="text-xl font-black text-white">{value}</p>
                  <p className="mt-1 text-xs font-bold text-gray-400">{label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <section className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.14em] text-cyan-100">
                <Share2 size={17} />
                Unde merge gratis
              </p>
              <h2 className="mt-2 text-2xl font-black text-white">
                Canale unde are sens sa apari organic.
              </h2>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {channels.map((channel) => {
              const Icon = channel.icon;

              return (
                <article key={channel.title} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                  <span
                    className={`flex h-10 w-10 items-center justify-center rounded-lg border ${toneClass(
                      channel.tone
                    )}`}
                  >
                    <Icon size={18} />
                  </span>
                  <h3 className="mt-4 text-lg font-black text-white">{channel.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-gray-400">{channel.text}</p>
                </article>
              );
            })}
          </div>
        </section>

        <OrganicPromotionKit />

        <section className="grid gap-5 rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
          <div>
            <p className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.14em] text-emerald-100">
              <ShieldCheck size={17} />
              Reguli anti-spam
            </p>
            <h2 className="mt-2 text-2xl font-black text-white">
              Crestere curata, fara sa enervezi oamenii.
            </h2>
            <p className="mt-2 text-sm leading-6 text-gray-400">
              Mesajele merg mai bine cand sunt transparente: spui ce construiesti, ceri feedback si nu fortezi nimic.
            </p>
          </div>

          <div className="grid gap-3">
            {rules.map((rule) => (
              <div key={rule} className="flex gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-4">
                <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-200" size={18} />
                <p className="text-sm font-semibold leading-6 text-gray-200">{rule}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-4 rounded-lg border border-emerald-300/20 bg-emerald-300/10 p-5 sm:grid-cols-[1fr_auto] sm:items-center">
          <div>
            <p className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.14em] text-emerald-100">
              <Megaphone size={17} />
              Pasul practic
            </p>
            <h2 className="mt-2 text-2xl font-black text-white">
              Posteaza 1 mesaj, apoi raspunde la fiecare feedback.
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-300">
              Mai bine 5 conversatii reale decat 50 de postari reci. Noteaza produsele lipsa si intrebarile care se repeta.
            </p>
          </div>
          <Link
            href="/catalog-romania"
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
          >
            Deschide catalogul
            <ArrowRight size={18} />
          </Link>
        </section>
      </section>
    </main>
  );
}

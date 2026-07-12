"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Check,
  Copy,
  ExternalLink,
  Gift,
  MessageCircle,
  Search,
  Share2,
  Sparkles,
  Users,
  Video,
} from "lucide-react";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://www.cealeg.shop").replace(/\/$/, "");

const quickLinks = [
  {
    id: "catalog",
    label: "Catalog Romania",
    href: "/catalog-romania",
    detail: "pagina buna pentru grupuri si Google",
  },
  {
    id: "missing",
    label: "Adauga produs lipsa",
    href: "/submit-product",
    detail: "trimite produse negasite la verificare",
  },
  {
    id: "lidl",
    label: "Pagina Lidl",
    href: "/catalog-romania/magazine/lidl",
    detail: "exemplu bun pentru scanari la magazin",
  },
  {
    id: "iaurturi",
    label: "Alternative la iaurturi",
    href: "/catalog-romania/alternative/iaurturi",
    detail: "link bun pentru postari despre zahar",
  },
];

const templates = [
  {
    id: "facebook-testers",
    channel: "Facebook grupuri",
    title: "Postare pentru testeri",
    icon: Users,
    tone: "emerald",
    link: "/catalog-romania",
    tip: "Buna pentru grupuri locale, cumparaturi, parinti, fitness sau nutritie.",
    text: [
      "Lucrez la Ce aleg?, o aplicatie romaneasca unde scanezi codul de bare si vezi rapid daca un produs merita sau daca exista alternative mai bune.",
      "",
      "Catalogul pentru Romania inca se construieste, asa ca ma ajuta mult feedback real din magazine: Lidl, Kaufland, Carrefour, Mega Image, Profi, Penny sau marketuri locale.",
      "",
      "Daca scanezi un produs care nu exista in catalog, il poti trimite la verificare cu poza la ambalaj si tabelul nutritional. Dupa aprobare primesti CeCoins.",
      "",
      "Nu vand nimic in postarea asta. Caut oameni care sa testeze si sa imi spuna ce nu e clar, ce lipseste si ce ar face aplicatia mai utila la cumparaturi.",
    ].join("\n"),
  },
  {
    id: "whatsapp",
    channel: "WhatsApp",
    title: "Mesaj scurt pentru prieteni",
    icon: MessageCircle,
    tone: "cyan",
    link: "/catalog-romania",
    tip: "Trimite-l la oameni care merg des la cumparaturi sau au copii.",
    text: [
      "Am lansat/testez Ce aleg?, o aplicatie unde scanezi codul de bare si vezi rapid informatii despre produs, alternative si scor.",
      "",
      "Daca ai 2 minute cand esti la magazin, incearca sa scanezi 1-2 produse. Daca nu apar in catalog, le poti trimite la verificare si ajuti catalogul pentru Romania.",
      "",
      "Orice feedback sincer ma ajuta mult.",
    ].join("\n"),
  },
  {
    id: "reels",
    channel: "TikTok / Reels",
    title: "Script pentru clip scurt",
    icon: Video,
    tone: "amber",
    link: "/barcode-scan",
    tip: "Clip de 15-25 secunde, filmat direct la raft.",
    text: [
      "Cadru 1: Sunt la magazin si nu stiu ce produs sa aleg.",
      "Cadru 2: Deschid Ce aleg? si scanez codul de bare.",
      "Cadru 3: Vad scorul, informatiile si alternativele.",
      "Cadru 4: Daca produsul nu exista, il trimit la verificare cu poze.",
      "Cadru 5: Catalogul Romania creste cu produse reale scanate de oameni.",
      "",
      "Text pe ecran: Scaneaza produsul. Compara. Ajuta catalogul Romaniei.",
    ].join("\n"),
  },
  {
    id: "comment-reply",
    channel: "Comentarii",
    title: "Raspuns rapid cand cineva intreaba",
    icon: Search,
    tone: "white",
    link: "/catalog-romania/produse",
    tip: "Foloseste-l la intrebari despre produse, etichete sau alternative.",
    text: [
      "Poti incerca Ce aleg? aici. E o aplicatie romaneasca unde scanezi codul de bare si vezi rapid informatii despre produs si alternative.",
      "",
      "Catalogul inca se completeaza, deci daca produsul lipseste il poti trimite la verificare. Asta ajuta mult pentru produse din Romania.",
    ].join("\n"),
  },
  {
    id: "product-missing",
    channel: "Contributii catalog",
    title: "Chemare pentru produse lipsa",
    icon: Sparkles,
    tone: "rose",
    link: "/submit-product",
    tip: "Buna cand vrei sa strangi produse reale din magazine.",
    text: [
      "Ai scanat un produs si nu apare in catalog?",
      "",
      "Trimite-l la verificare in Ce aleg?: codul de bare este completat automat, faci poza la fata produsului si la tabelul nutritional, iar OCR-ul completeaza ce poate.",
      "",
      "Dupa aprobare primesti CeCoins si produsul devine util pentru toti cei care il scaneaza dupa tine.",
    ].join("\n"),
  },
];

function toneClasses(tone) {
  const map = {
    emerald: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100",
    cyan: "border-cyan-300/25 bg-cyan-300/10 text-cyan-100",
    amber: "border-amber-300/25 bg-amber-300/10 text-amber-100",
    rose: "border-rose-300/25 bg-rose-300/10 text-rose-100",
    white: "border-white/15 bg-white/[0.05] text-white",
  };

  return map[tone] || map.emerald;
}

function copyWithFallback(text) {
  if (navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);

  return Promise.resolve();
}

export default function OrganicPromotionKit() {
  const [copiedId, setCopiedId] = useState("");

  const preparedTemplates = useMemo(
    () =>
      templates.map((template) => ({
        ...template,
        href: `${SITE_URL}${template.link}`,
        copyText: `${template.text}\n\n${SITE_URL}${template.link}`,
      })),
    []
  );

  async function handleCopy(id, text) {
    try {
      await copyWithFallback(text);
      setCopiedId(id);
      window.setTimeout(() => setCopiedId((current) => (current === id ? "" : current)), 1800);
    } catch {
      setCopiedId("");
    }
  }

  return (
    <section id="texte" className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)]">
        <div className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15">
          <div className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.14em] text-emerald-100">
            <Share2 size={17} />
            Linkuri bune de trimis
          </div>
          <h2 className="mt-3 text-2xl font-black text-white">
            Alege linkul potrivit pentru context.
          </h2>
          <p className="mt-2 text-sm leading-6 text-gray-400">
            Trimite pagina generala cand omul nu stie aplicatia. Trimite o pagina de magazin sau alternativa cand discutia e deja despre produse.
          </p>

          <div className="mt-5 grid gap-3">
            {quickLinks.map((item) => {
              const absoluteUrl = `${SITE_URL}${item.href}`;
              const isCopied = copiedId === item.id;

              return (
                <article
                  key={item.id}
                  className="grid gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-4 sm:grid-cols-[1fr_auto] sm:items-center"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-black text-white">{item.label}</p>
                    <p className="mt-1 text-xs leading-5 text-gray-400">{item.detail}</p>
                    <p className="mt-2 truncate text-xs font-semibold text-cyan-100">{absoluteUrl}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleCopy(item.id, absoluteUrl)}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/15 bg-white/[0.05] text-white transition hover:bg-white/[0.1]"
                      aria-label={`Copiaza ${item.label}`}
                    >
                      {isCopied ? <Check size={17} /> : <Copy size={17} />}
                    </button>
                    <Link
                      href={item.href}
                      className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white text-black transition hover:bg-cyan-100"
                      aria-label={`Deschide ${item.label}`}
                    >
                      <ExternalLink size={17} />
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <div className="rounded-lg border border-emerald-300/20 bg-emerald-300/10 p-5 shadow-xl shadow-black/15">
          <div className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.14em] text-emerald-100">
            <Gift size={17} />
            Cum il folosesti
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {[
              "Alegi canalul: grup, WhatsApp, clip sau comentariu.",
              "Copiaza textul si schimba-l putin ca sa sune natural.",
              "Raspunde la feedback si noteaza ce produse lipsesc.",
            ].map((step, index) => (
              <article key={step} className="rounded-lg border border-white/10 bg-black/20 p-4">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-black text-black">
                  {index + 1}
                </span>
                <p className="mt-4 text-sm font-bold leading-6 text-gray-100">{step}</p>
              </article>
            ))}
          </div>
          <p className="mt-5 rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-gray-200">
            Cel mai bun mesaj este simplu: aplicatia e in lucru, catalogul creste prin scanari reale si cauti feedback, nu spam.
          </p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {preparedTemplates.map((template) => {
          const Icon = template.icon;
          const isCopied = copiedId === template.id;

          return (
            <article
              key={template.id}
              className="rounded-lg border border-white/10 bg-[#101820]/82 p-5 shadow-xl shadow-black/15"
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex min-w-0 items-start gap-3">
                  <span
                    className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border ${toneClasses(
                      template.tone
                    )}`}
                  >
                    <Icon size={20} />
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-black uppercase tracking-[0.14em] text-gray-400">
                      {template.channel}
                    </p>
                    <h3 className="mt-1 text-xl font-black text-white">{template.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-gray-400">{template.tip}</p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleCopy(template.id, template.copyText)}
                  className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-black text-black transition hover:-translate-y-0.5 hover:bg-cyan-100"
                >
                  {isCopied ? <Check size={17} /> : <Copy size={17} />}
                  {isCopied ? "Copiat" : "Copiaza"}
                </button>
              </div>

              <pre className="mt-5 max-h-[22rem] overflow-auto whitespace-pre-wrap rounded-lg border border-white/10 bg-black/25 p-4 text-sm leading-6 text-gray-200">
                {template.copyText}
              </pre>
            </article>
          );
        })}
      </div>
    </section>
  );
}

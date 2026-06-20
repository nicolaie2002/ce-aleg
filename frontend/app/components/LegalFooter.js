"use client";

import Link from "next/link";
import Image from "next/image";
import {
  Barcode,
  Camera,
  Crown,
  LockKeyhole,
  Mail,
  RotateCcwKey,
  Scale,
  ShieldCheck,
} from "lucide-react";
import { useLocale } from "./LocaleProvider";

export function LegalFooter() {
  const { pick } = useLocale();

  const productLinks = [
    { href: "/barcode-scan", label: pick("Scanare cod", "Barcode scan"), icon: Barcode },
    { href: "/live-assistant", label: pick("Asistent live", "Live assistant"), icon: Camera },
    { href: "/pricing", label: pick("Planuri", "Plans"), icon: Crown },
  ];

  const accountLinks = [
    { href: "/forgot-password", label: pick("Resetare parola", "Reset password"), icon: RotateCcwKey },
    { href: "/privacy", label: pick("Confidentialitate", "Privacy"), icon: LockKeyhole },
    { href: "/terms", label: pick("Termeni", "Terms"), icon: Scale },
  ];

  return (
    <footer className="ce-footer mt-auto border-t border-white/10">
      <div className="ce-shell py-10">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)]">
          <div className="max-w-xl">
            <Link href="/" className="inline-flex items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-xl shadow-[0_0_30px_rgba(52,211,153,.22)]">
                <Image
                  src="/icon.png"
                  alt="Ce aleg?"
                  width={96}
                  height={96}
                  className="h-full w-full object-cover"
                  unoptimized
                />
              </span>
              <span>
                <span className="block text-xl font-black text-white">Ce aleg?</span>
                <span className="text-xs font-bold text-cyan-100/75">
                  {pick("cumparaturi mai clare", "clearer shopping")}
                </span>
              </span>
            </Link>
            <p className="mt-5 max-w-md leading-7 text-gray-300">
              {pick(
                "Scanezi un produs, vezi informatiile importante si alegi alternative potrivite pentru bugetul si preferintele tale.",
                "Scan a product, see what matters and choose alternatives that match your budget and preferences."
              )}
            </p>
            <div className="mt-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.045] px-3 py-2 text-xs font-bold text-gray-300">
              <ShieldCheck size={15} className="text-cyan-200" />
              {pick("Cont, cos si istoric protejate", "Protected account, cart and history")}
            </div>
          </div>

          <nav aria-label={pick("Produs", "Product")}>
            <h2 className="text-sm font-black uppercase tracking-wide text-white/80">
              {pick("Produs", "Product")}
            </h2>
            <div className="mt-4 space-y-3">
              {productLinks.map(({ href, label, icon: Icon }) => (
                <Link key={href} href={href} className="flex items-center gap-2 text-sm font-semibold text-gray-300 hover:text-white">
                  <Icon size={15} className="text-cyan-200" />
                  {label}
                </Link>
              ))}
            </div>
          </nav>

          <nav aria-label={pick("Cont si legal", "Account and legal")}>
            <h2 className="text-sm font-black uppercase tracking-wide text-white/80">
              {pick("Cont", "Account")}
            </h2>
            <div className="mt-4 space-y-3">
              {accountLinks.map(({ href, label, icon: Icon }) => (
                <Link key={href} href={href} className="flex items-center gap-2 text-sm font-semibold text-gray-300 hover:text-white">
                  <Icon size={15} className="text-cyan-200" />
                  {label}
                </Link>
              ))}
            </div>
          </nav>

          <div>
            <h2 className="text-sm font-black uppercase tracking-wide text-white/80">
              {pick("Contact", "Contact")}
            </h2>
            <a
              href="mailto:cealegshop@gmail.com"
              className="mt-4 flex items-center gap-2 text-sm font-semibold text-gray-300 hover:text-white"
            >
              <Mail size={15} className="text-cyan-200" />
              cealegshop@gmail.com
            </a>
            <p className="mt-4 text-sm leading-6 text-gray-400">
              {pick(
                "Informatiile despre produse sunt orientative si nu inlocuiesc sfatul unui medic sau nutritionist.",
                "Product information is guidance only and does not replace advice from a doctor or nutritionist."
              )}
            </p>
          </div>
        </div>

        <div className="mt-9 flex flex-col gap-3 border-t border-white/10 pt-5 text-xs text-gray-500 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Ce aleg?</p>
          <p>{pick("Construit pentru alegeri mai bune la raft.", "Built for better choices at the shelf.")}</p>
        </div>
      </div>
    </footer>
  );
}

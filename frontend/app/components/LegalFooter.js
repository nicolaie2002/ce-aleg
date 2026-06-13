"use client";

import Link from "next/link";
import { LockKeyhole, RotateCcwKey, Scale, ShieldCheck } from "lucide-react";
import { useLocale } from "./LocaleProvider";

export function LegalFooter() {
  const { pick } = useLocale();

  return (
    <footer className="mt-auto border-t border-white/10 bg-[#080d12]/72 py-7 text-sm text-gray-400 backdrop-blur">
      <div className="ce-shell flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-2xl">
          <p className="flex items-center gap-2 font-black text-white">
            <ShieldCheck size={17} className="text-emerald-300" />
            Ce aleg?
          </p>
          <p className="mt-2 leading-6">
            {pick(
              "Informatiile despre produse sunt orientative si nu inlocuiesc sfatul unui medic sau nutritionist.",
              "Product information is for guidance and does not replace advice from a doctor or nutritionist."
            )}
          </p>
        </div>

        <nav className="flex flex-wrap gap-x-5 gap-y-3" aria-label={pick("Informatii legale", "Legal information")}>
          <Link href="/privacy" className="inline-flex items-center gap-2 font-semibold hover:text-emerald-300">
            <LockKeyhole size={15} />
            {pick("Confidentialitate", "Privacy")}
          </Link>
          <Link href="/terms" className="inline-flex items-center gap-2 font-semibold hover:text-emerald-300">
            <Scale size={15} />
            {pick("Termeni", "Terms")}
          </Link>
          <Link href="/forgot-password" className="inline-flex items-center gap-2 font-semibold hover:text-emerald-300">
            <RotateCcwKey size={15} />
            {pick("Resetare parola", "Reset password")}
          </Link>
        </nav>
      </div>
    </footer>
  );
}

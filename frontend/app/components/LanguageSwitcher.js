"use client";

import { Globe2 } from "lucide-react";
import { useLocale } from "./LocaleProvider";

export function LanguageSwitcher({ compact = false }) {
  const { locale, setLocale, pick } = useLocale();

  return (
    <div
      className="inline-flex items-center gap-1 rounded-lg border border-white/15 bg-black/25 p-1"
      role="group"
      aria-label={pick("Selecteaza limba", "Select language")}
      title={pick("Schimba limba", "Change language")}
      suppressHydrationWarning
    >
      {!compact && <Globe2 size={15} className="ml-1 text-emerald-300" />}
      {["ro", "en"].map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => setLocale(option)}
          className={`min-h-9 min-w-9 rounded-md px-2 py-1 text-xs font-black uppercase ${
            locale === option
              ? "bg-emerald-400 text-black"
              : "text-gray-300 hover:bg-white/10 hover:text-white"
          }`}
          aria-pressed={locale === option}
          aria-label={option === "ro" ? "Română" : "English"}
          suppressHydrationWarning
        >
          {option}
        </button>
      ))}
    </div>
  );
}

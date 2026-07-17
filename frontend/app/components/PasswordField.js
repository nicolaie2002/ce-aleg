"use client";

import { useId, useState } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";
import { useLocale } from "./LocaleProvider";

export function PasswordField({
  label,
  value,
  onChange,
  placeholder,
  minLength,
  autoComplete,
  required = true,
}) {
  const { pick } = useLocale();
  const inputId = useId();
  const [isVisible, setIsVisible] = useState(false);
  const inputType = isVisible ? "text" : "password";

  return (
    <div className="block text-sm font-semibold text-gray-300">
      <label htmlFor={inputId} className="flex items-center gap-2">
        <LockKeyhole size={15} className="text-emerald-300" aria-hidden="true" />
        {label}
      </label>

      <span className="relative mt-2 block">
        <input
          id={inputId}
          type={inputType}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          minLength={minLength}
          placeholder={placeholder}
          autoComplete={autoComplete}
          className="w-full rounded-lg border border-white/10 bg-black/30 px-4 py-3 pr-12 text-white outline-none focus:border-emerald-400"
          required={required}
        />
        <button
          type="button"
          onClick={() => setIsVisible((current) => !current)}
          className="absolute right-2 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-lg text-gray-300 hover:bg-white/10 hover:text-emerald-300"
          aria-label={
            isVisible
              ? pick("Ascunde parola", "Hide password")
              : pick("Arată parola", "Show password")
          }
          title={
            isVisible
              ? pick("Ascunde parola", "Hide password")
              : pick("Arată parola", "Show password")
          }
        >
          {isVisible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
        </button>
      </span>
    </div>
  );
}

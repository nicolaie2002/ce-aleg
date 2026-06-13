"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, LockKeyhole } from "lucide-react";
import { API_URL } from "../config";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { PasswordField } from "../components/PasswordField";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";
import {
  PASSWORD_MIN_LENGTH,
  getPasswordStrength,
  getPasswordStrengthLabel,
} from "../utils/passwordStrength";

export default function ResetPasswordPage() {
  const { pick } = useLocale();
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const strength = useMemo(() => getPasswordStrength(password), [password]);

  async function handleSubmit(event) {
    event.preventDefault();
    setIsLoading(true);
    setErrorMessage("");

    try {
      const token = new URLSearchParams(window.location.search).get("token") || "";
      const response = await fetch(`${API_URL}/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || pick("Parola nu a putut fi schimbata.", "The password could not be changed."));
      }

      localStorage.setItem("cealeg_user", JSON.stringify(data.user));
      window.location.assign("/dashboard");
    } catch (error) {
      setErrorMessage(error.message || pick("A aparut o eroare.", "An error occurred."));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <section className="ce-shell-sm flex min-h-screen flex-col justify-center py-10">
        <div className="mb-8 flex items-center justify-between gap-3">
          <Link href="/login" className="inline-flex items-center gap-2 text-sm text-emerald-300 hover:text-emerald-200">
            <ArrowLeft size={16} /> {pick("Inapoi la login", "Back to login")}
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitcher compact />
            <ThemeSwitcher />
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#0d141b]/95 p-6 shadow-2xl">
          <p className="text-sm font-black text-emerald-300">{pick("Securitate cont", "Account security")}</p>
          <h1 className="mt-3 text-4xl font-black">{pick("Alege o parola noua", "Choose a new password")}</h1>
          <p className="mt-3 leading-7 text-gray-300">
            {pick(
              "Parola trebuie sa aiba minimum 8 caractere. O parola mai lunga este mai greu de ghicit.",
              "The password must have at least 8 characters. A longer password is harder to guess."
            )}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <PasswordField
              label={pick("Parola noua", "New password")}
              value={password}
              onChange={setPassword}
              minLength={PASSWORD_MIN_LENGTH}
              placeholder={pick("minimum 8 caractere", "minimum 8 characters")}
              autoComplete="new-password"
            />

            {password && (
              <div className="rounded-lg border border-white/10 bg-black/25 p-3">
                <div className="flex items-center justify-between text-xs font-black">
                  <span className="text-gray-300">{pick("Putere parola", "Password strength")}</span>
                  <span className="text-emerald-300">{getPasswordStrengthLabel(strength, pick)}</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className={`h-full ${strength.color}`}
                    style={{ width: `${strength.percent}%` }}
                  />
                </div>
                {strength.suggestions.length > 0 && (
                  <p className="mt-2 text-xs leading-5 text-gray-400">
                    {strength.suggestions[0]}
                  </p>
                )}
              </div>
            )}

            {errorMessage && (
              <div className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-red-300">
                {errorMessage}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className={`inline-flex w-full items-center justify-center gap-2 rounded-lg px-6 py-4 font-black ${
                isLoading
                  ? "cursor-not-allowed bg-white/10 text-gray-400"
                  : "bg-emerald-400 text-black hover:bg-emerald-300"
              }`}
            >
              <LockKeyhole size={18} />
              {isLoading ? pick("Se salveaza...", "Saving...") : pick("Schimba parola", "Change password")}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}

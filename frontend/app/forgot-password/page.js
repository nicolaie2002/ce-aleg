"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mail, Send } from "lucide-react";
import { API_URL } from "../config";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";

export default function ForgotPasswordPage() {
  const { pick } = useLocale();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [devResetLink, setDevResetLink] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setIsLoading(true);
    setMessage("");
    setErrorMessage("");
    setDevResetLink("");

    try {
      const response = await fetch(`${API_URL}/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || pick("Nu am putut trimite cererea.", "We could not send the request."));
      }

      setMessage(data.message || pick("Verifică emailul pentru linkul de resetare.", "Check your email for the reset link."));
      if (data.devResetLink) {
        setDevResetLink(data.devResetLink);
      }
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
            <ArrowLeft size={16} /> {pick("Înapoi la login", "Back to login")}
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitcher compact />
            <ThemeSwitcher />
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#0d141b]/95 p-6 shadow-2xl">
          <p className="text-sm font-black text-emerald-300">{pick("Recuperare cont", "Account recovery")}</p>
          <h1 className="mt-3 text-4xl font-black">{pick("Ai uitat parola?", "Forgot password?")}</h1>
          <p className="mt-3 leading-7 text-gray-300">
            {pick(
              "Introdu emailul contului și îți trimitem un link de resetare.",
              "Enter your account email and we will send a reset link."
            )}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <label className="block text-sm font-semibold text-gray-300">
              <span className="flex items-center gap-2"><Mail size={15} className="text-emerald-300" /> Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="email@example.com"
                className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-emerald-400"
                required
              />
            </label>

            {message && (
              <div className="rounded-lg border border-emerald-300/25 bg-emerald-400/10 p-4 text-emerald-100">
                {message}
              </div>
            )}
            {errorMessage && (
              <div className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-red-300">
                {errorMessage}
              </div>
            )}
            {devResetLink && (
              <Link
                href={devResetLink.replace(/^https?:\/\/[^/]+/, "")}
                className="block rounded-lg border border-yellow-300/25 bg-yellow-300/10 p-4 text-sm font-bold text-yellow-100 hover:bg-yellow-300/20"
              >
                {pick("Link local de test: deschide resetarea parolei", "Local test link: open password reset")}
              </Link>
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
              <Send size={18} />
              {isLoading ? pick("Se trimite...", "Sending...") : pick("Trimite linkul", "Send reset link")}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}

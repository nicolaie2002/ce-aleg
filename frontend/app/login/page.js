"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, Crown, LogIn, Mail, ShieldCheck } from "lucide-react";
import { API_URL } from "../config";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { PasswordField } from "../components/PasswordField";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";
import { readApiJson } from "../utils/apiResponse";

function getSafeDestination() {
  const nextPath = new URLSearchParams(window.location.search).get("next");

  if (!nextPath || !nextPath.startsWith("/") || nextPath.startsWith("//")) {
    return "/dashboard";
  }

  try {
    const destination = new URL(nextPath, window.location.origin);
    return destination.origin === window.location.origin
      ? `${destination.pathname}${destination.search}${destination.hash}`
      : "/dashboard";
  } catch {
    return "/dashboard";
  }
}

export default function LoginPage() {
  const { pick } = useLocale();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [verificationNotice, setVerificationNotice] = useState("");
  const [needsVerification, setNeedsVerification] = useState(false);
  const [isResendingVerification, setIsResendingVerification] = useState(false);

  async function handleLogin(event) {
    event.preventDefault();
    setIsLoading(true);
    setErrorMessage("");
    setVerificationNotice("");
    setNeedsVerification(false);

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        if (data.code === "email_not_verified") {
          setNeedsVerification(true);
        }
        throw new Error(data.error || pick("Autentificare esuata.", "Sign-in failed."));
      }

      localStorage.setItem("cealeg_user", JSON.stringify(data.user));
      const destination = getSafeDestination();
      const sessionResponse = await fetch(`${API_URL}/auth/me`, { cache: "no-store" });

      if (!sessionResponse.ok) {
        throw new Error(
          pick(
            "Sesiunea nu a fost salvata corect. Reincearca dupa refresh.",
            "The session was not saved correctly. Refresh and try again."
          )
        );
      }

      window.location.assign(destination);
    } catch (error) {
      setErrorMessage(
        error.message || pick("A aparut o eroare la autentificare.", "A sign-in error occurred.")
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function resendVerificationEmail() {
    setIsResendingVerification(true);
    setVerificationNotice("");
    setErrorMessage("");

    try {
      const response = await fetch(`${API_URL}/auth/resend-verification`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || pick("Emailul nu a putut fi retrimis.", "The email could not be resent."));
      }

      setVerificationNotice(data.message || pick("Am trimis un nou link de confirmare.", "We sent a new confirmation link."));
    } catch (error) {
      setErrorMessage(error.message || pick("Emailul nu a putut fi retrimis.", "The email could not be resent."));
    } finally {
      setIsResendingVerification(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <section className="ce-shell-md flex min-h-screen flex-col justify-center py-10">
        <div className="mb-8 flex items-center justify-between gap-3">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-emerald-300 hover:text-emerald-200">
            <ArrowLeft size={16} /> {pick("Pagina principală", "Home")}
          </Link>
          <div className="flex items-center gap-2">
            <Link href="/pricing" className="inline-flex items-center gap-1 rounded-lg border border-yellow-300/35 px-3 py-2 text-sm font-black text-yellow-200 hover:bg-yellow-300/10">
              <Crown size={15} /> {pick("Planuri", "Plans")}
            </Link>
            <LanguageSwitcher compact />
            <ThemeSwitcher />
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_460px] lg:items-center">
          <div className="hidden rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(16,185,129,0.14),rgba(250,204,21,0.08),rgba(255,255,255,0.04))] p-8 shadow-2xl lg:block">
            <p className="text-sm font-black text-emerald-300">Ce aleg?</p>
            <h2 className="mt-4 text-5xl font-black leading-tight">
              {pick("Cumpărături mai clare, fără ghicit.", "Clearer shopping, less guessing.")}
            </h2>
            <p className="mt-5 max-w-xl leading-8 text-gray-300">
              {pick(
                "Păstrează istoricul, coșul și preferințele într-un singur loc.",
                "Keep history, cart and preferences in one place."
              )}
            </p>
          </div>

          <div className="rounded-lg border border-white/10 bg-[#0d141b]/95 p-6 shadow-2xl shadow-black/30">
            <div className="mb-5 flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center overflow-hidden rounded-lg">
                <Image
                  src="/icon.png"
                  alt="Ce aleg?"
                  width={88}
                  height={88}
                  className="h-full w-full object-cover"
                  priority
                />
              </span>
              <span>
                <span className="block font-black">Ce aleg?</span>
                <span className="text-xs text-gray-400">
                  {pick("cont personal de cumpărături", "personal shopping account")}
                </span>
              </span>
            </div>
            <h1 className="text-3xl font-bold">{pick("Bine ai revenit", "Welcome back")}</h1>
            <p className="mt-3 text-gray-300">
              {pick(
                "Intră în cont ca să vezi coșul, istoricul și produsele favorite.",
                "Sign in to view your cart, history and favorite products."
              )}
            </p>

            <form onSubmit={handleLogin} className="mt-6 space-y-4">
              <label className="block text-sm font-semibold text-gray-300">
                <span className="flex items-center gap-2"><Mail size={15} className="text-emerald-300" /> Email</span>
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-emerald-400"
                  autoComplete="email"
                  required
                />
              </label>

              <PasswordField
                label={pick("Parola", "Password")}
                value={password}
                onChange={setPassword}
                autoComplete="current-password"
              />

              <div className="flex justify-end">
                <Link href="/forgot-password" className="text-sm font-semibold text-emerald-300 hover:text-emerald-200">
                  {pick("Ai uitat parola?", "Forgot password?")}
                </Link>
              </div>

              {errorMessage && (
                <div className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-red-300">
                  <p>{errorMessage}</p>
                  {needsVerification && (
                    <button
                      type="button"
                      onClick={resendVerificationEmail}
                      disabled={isResendingVerification || !email.trim()}
                      className="mt-3 inline-flex rounded-lg bg-white px-4 py-2 text-sm font-black text-black hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isResendingVerification
                        ? pick("Se trimite...", "Sending...")
                        : pick("Retrimite emailul", "Resend email")}
                    </button>
                  )}
                </div>
              )}

              {verificationNotice && (
                <div className="rounded-lg border border-cyan-300/30 bg-cyan-300/10 p-4 text-cyan-100">
                  {verificationNotice}
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className={`inline-flex w-full items-center justify-center gap-2 rounded-lg px-6 py-3.5 font-semibold ${
                  isLoading
                    ? "cursor-not-allowed bg-white/10 text-gray-400"
                    : "bg-emerald-400 text-black hover:bg-emerald-300"
                }`}
              >
                <LogIn size={18} />
                {isLoading ? pick("Se autentifica...", "Signing in...") : pick("Autentificare", "Sign in")}
              </button>
            </form>

            <p className="mt-5 flex items-center justify-center gap-2 text-xs text-gray-500">
              <ShieldCheck size={14} className="text-emerald-300" />
              {pick("Sesiunea este protejata in browserul tau.", "Your session is protected in your browser.")}
            </p>
            <p className="mt-5 text-center text-sm text-gray-400">
              {pick("Nu ai cont?", "No account yet?")}{" "}
              <Link href="/register" className="font-semibold text-emerald-300 hover:text-emerald-200">
                {pick("Creează cont", "Create account")}
              </Link>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

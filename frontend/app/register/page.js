"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Crown, MailCheck, UserPlus } from "lucide-react";
import { API_URL } from "../config";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { PasswordField } from "../components/PasswordField";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";
import { readApiJson } from "../utils/apiResponse";
import {
  PASSWORD_MIN_LENGTH,
  getPasswordStrength,
  getPasswordStrengthLabel,
} from "../utils/passwordStrength";

export default function RegisterPage() {
  const { pick } = useLocale();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [ageConfirmed, setAgeConfirmed] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [devVerificationLink, setDevVerificationLink] = useState("");
  const strength = useMemo(() => getPasswordStrength(password), [password]);

  async function handleRegister(event) {
    event.preventDefault();
    setIsLoading(true);
    setErrorMessage("");
    setSuccessMessage("");
    setDevVerificationLink("");

    try {
      const response = await fetch(`${API_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim().toLowerCase(),
          password,
          ageConfirmed,
          acceptedTerms,
        }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(
          data.error ||
            pick("Nu s-a putut crea contul.", "The account could not be created.")
        );
      }

      setSuccessMessage(
        data.message ||
          pick(
            "Cont creat. Verifica emailul ca sa il activezi.",
            "Account created. Check your email to activate it."
          )
      );
      setDevVerificationLink(data.emailStatus?.devVerificationLink || "");
      setPassword("");
    } catch (error) {
      setErrorMessage(
        error.message ||
          pick("A aparut o eroare la crearea contului.", "An account creation error occurred.")
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <section className="ce-shell-md flex min-h-screen flex-col justify-center py-10">
        <div className="mb-8 flex items-center justify-between gap-3">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-emerald-300 hover:text-emerald-200">
            <ArrowLeft size={16} /> {pick("Pagina principala", "Home")}
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
              {pick("Incepe cu alegeri mai bune.", "Start choosing better.")}
            </h2>
            <p className="mt-5 max-w-xl leading-8 text-gray-300">
              {pick(
                "Contul pastreaza cosul, favoritele si preferintele pentru recomandari mai potrivite.",
                "Your account keeps your cart, favorites and preferences for better recommendations."
              )}
            </p>
          </div>

          <div className="rounded-lg border border-white/10 bg-[#0d141b]/95 p-6 shadow-2xl">
            <p className="text-sm font-bold text-emerald-300">{pick("Cont nou", "New account")}</p>
            <h1 className="mt-3 text-4xl font-bold">{pick("Creeaza cont", "Create account")}</h1>
            <p className="mt-3 text-gray-300">
              {pick(
                "Alege o parola de minimum 8 caractere. Iti vom arata cat de puternica este.",
                "Choose a password with at least 8 characters. We will show how strong it is."
              )}
            </p>

            <form onSubmit={handleRegister} className="mt-6 space-y-4">
              <label className="block text-sm font-semibold text-gray-300">
                {pick("Nume", "Name")}
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder={pick("Ex: Andrei", "Example: Alex")}
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-emerald-400"
                  required
                />
              </label>

              <label className="block text-sm font-semibold text-gray-300">
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="email@example.com"
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-4 py-3 text-white outline-none focus:border-emerald-400"
                  required
                />
              </label>

              <PasswordField
                label={pick("Parola", "Password")}
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

              {successMessage && (
                <div className="rounded-lg border border-cyan-300/30 bg-cyan-300/10 p-4 text-cyan-100">
                  <p className="flex items-center gap-2 font-black">
                    <MailCheck size={18} />
                    {successMessage}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-cyan-50/80">
                    {pick(
                      "Dupa confirmare te vom trimite automat in cont.",
                      "After confirmation we will send you into your account automatically."
                    )}
                  </p>
                  {devVerificationLink && (
                    <Link
                      href={devVerificationLink}
                      className="mt-3 inline-flex rounded-lg bg-white px-4 py-2 text-sm font-black text-black hover:bg-cyan-100"
                    >
                      {pick("Deschide linkul local de confirmare", "Open local confirmation link")}
                    </Link>
                  )}
                </div>
              )}

              <label className="flex gap-3 rounded-lg border border-white/10 bg-black/20 p-3 text-sm leading-6 text-gray-300">
                <input
                  type="checkbox"
                  checked={ageConfirmed}
                  onChange={(event) => setAgeConfirmed(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-white/20 accent-emerald-400"
                  required
                />
                <span>
                  {pick(
                    "Confirm ca am cel putin 16 ani sau folosesc aplicatia cu acordul parintelui/tutorelui.",
                    "I confirm that I am at least 16 or that I use the app with parent/guardian consent."
                  )}
                </span>
              </label>

              <label className="flex gap-3 rounded-lg border border-white/10 bg-black/20 p-3 text-sm leading-6 text-gray-300">
                <input
                  type="checkbox"
                  checked={acceptedTerms}
                  onChange={(event) => setAcceptedTerms(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-white/20 accent-emerald-400"
                  required
                />
                <span>
                  {pick("Accept", "I accept")}{" "}
                  <Link href="/terms" className="font-bold text-emerald-300 hover:text-emerald-200">
                    {pick("Termenii si conditiile", "Terms and conditions")}
                  </Link>{" "}
                  {pick("si", "and")}{" "}
                  <Link href="/privacy" className="font-bold text-emerald-300 hover:text-emerald-200">
                    {pick("Politica de confidentialitate", "Privacy policy")}
                  </Link>
                  .
                </span>
              </label>

              <button
                type="submit"
                disabled={isLoading}
                className={`inline-flex w-full items-center justify-center gap-2 rounded-lg px-6 py-4 font-semibold ${
                  isLoading
                    ? "cursor-not-allowed bg-white/10 text-gray-400"
                    : "bg-emerald-400 text-black hover:bg-emerald-300"
                }`}
              >
                <UserPlus size={18} />
                {isLoading ? pick("Se creeaza contul...", "Creating account...") : pick("Creeaza cont", "Create account")}
              </button>
            </form>

            <p className="mt-5 text-center text-sm text-gray-400">
              {pick("Ai deja cont?", "Already have an account?")}{" "}
              <Link href="/login" className="font-semibold text-emerald-300 hover:text-emerald-200">
                {pick("Autentifica-te", "Sign in")}
              </Link>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

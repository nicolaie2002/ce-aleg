"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, ShieldAlert, Trash2 } from "lucide-react";
import { API_URL } from "../config";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";

export default function DeleteAccountPage() {
  const { pick } = useLocale();
  const [token] = useState(() => {
    if (typeof window === "undefined") return "";
    return new URLSearchParams(window.location.search).get("token") || "";
  });
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  async function confirmAccountDeletion() {
    setIsDeleting(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const response = await fetch(`${API_URL}/account/delete/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || pick("Contul nu a putut fi sters.", "The account could not be deleted."));
      }

      localStorage.removeItem("cealeg_user");
      localStorage.removeItem("cealeg_preferences");
      localStorage.removeItem("cealeg_email_status");
      setSuccessMessage(data.message || pick("Contul a fost sters.", "The account has been deleted."));
    } catch (error) {
      setErrorMessage(error.message || pick("A aparut o eroare.", "An error occurred."));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <section className="ce-shell-sm flex min-h-screen flex-col justify-center py-10">
        <div className="mb-8 flex items-center justify-between gap-3">
          <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm font-bold text-emerald-300 hover:text-emerald-200">
            <ArrowLeft size={16} /> {pick("Înapoi la dashboard", "Back to dashboard")}
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitcher compact />
            <ThemeSwitcher />
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#0d141b]/95 p-6 shadow-2xl">
          {successMessage ? (
            <div>
              <span className="flex h-14 w-14 items-center justify-center rounded-lg bg-emerald-400 text-black">
                <CheckCircle2 size={28} />
              </span>
              <p className="mt-6 text-sm font-black text-emerald-300">
                {pick("Cont sters", "Account deleted")}
              </p>
              <h1 className="mt-3 text-4xl font-black">
                {pick("Datele contului au fost eliminate.", "Your account data has been removed.")}
              </h1>
              <p className="mt-4 leading-7 text-gray-300">{successMessage}</p>
              <Link
                href="/"
                className="mt-7 inline-flex items-center justify-center rounded-lg bg-emerald-400 px-6 py-3 font-black text-black hover:bg-emerald-300"
              >
                {pick("Pagina principală", "Home")}
              </Link>
            </div>
          ) : (
            <div>
              <span className="flex h-14 w-14 items-center justify-center rounded-lg bg-red-400/15 text-red-300">
                <ShieldAlert size={28} />
              </span>
              <p className="mt-6 text-sm font-black text-red-300">
                {pick("Confirmare necesara", "Confirmation required")}
              </p>
              <h1 className="mt-3 text-4xl font-black">
                {pick("Ștergi definitiv contul?", "Delete your account permanently?")}
              </h1>
              <p className="mt-4 leading-7 text-gray-300">
                {pick(
                  "După confirmare, contul, istoricul, coșul, favoritele și contribuțiile tale vor fi șterse. Acțiunea nu poate fi anulată.",
                  "After confirmation, your account, history, cart, favorites and contributions will be deleted. This action cannot be undone."
                )}
              </p>

              {!token && (
                <div className="mt-6 rounded-lg border border-yellow-300/30 bg-yellow-300/10 p-4 text-yellow-100">
                  {pick(
                    "Linkul de confirmare lipseste. Deschide linkul primit pe email.",
                    "The confirmation link is missing. Open the link received by email."
                  )}
                </div>
              )}

              {errorMessage && (
                <div className="mt-6 rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-red-200">
                  {errorMessage}
                </div>
              )}

              <div className="mt-7 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={confirmAccountDeletion}
                  disabled={!token || isDeleting}
                  className={`inline-flex items-center justify-center gap-2 rounded-lg px-6 py-4 font-black ${
                    !token || isDeleting
                      ? "cursor-not-allowed bg-white/10 text-gray-400"
                      : "bg-red-400 text-black hover:bg-red-300"
                  }`}
                >
                  <Trash2 size={18} />
                  {isDeleting ? pick("Se șterge...", "Deleting...") : pick("Șterge contul definitiv", "Delete account permanently")}
                </button>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center rounded-lg border border-white/10 px-6 py-4 font-bold text-white hover:bg-white/10"
                >
                  {pick("Păstrează contul", "Keep account")}
                </Link>
              </div>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

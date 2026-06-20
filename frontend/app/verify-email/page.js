"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, MailCheck } from "lucide-react";
import { API_URL } from "../config";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { useLocale } from "../components/LocaleProvider";
import { readApiJson } from "../utils/apiResponse";

function VerifyEmailContent() {
  const { pick } = useLocale();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState(
    pick("Confirmam emailul...", "Confirming your email...")
  );

  useEffect(() => {
    let isMounted = true;

    async function verifyEmail() {
      if (!token) {
        setStatus("error");
        setMessage(pick("Linkul de confirmare lipseste.", "The confirmation link is missing."));
        return;
      }

      try {
        const response = await fetch(`${API_URL}/auth/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });
        const data = await readApiJson(response);

        if (!response.ok) {
          throw new Error(data.error || pick("Emailul nu a putut fi confirmat.", "The email could not be confirmed."));
        }

        localStorage.setItem("cealeg_user", JSON.stringify(data.user));
        if (data.emailStatus) {
          localStorage.setItem("cealeg_email_status", JSON.stringify(data.emailStatus));
        }

        if (!isMounted) return;
        setStatus("success");
        setMessage(data.message || pick("Email confirmat.", "Email confirmed."));
        window.setTimeout(() => window.location.assign("/dashboard"), 900);
      } catch (error) {
        if (!isMounted) return;
        setStatus("error");
        setMessage(error.message || pick("Emailul nu a putut fi confirmat.", "The email could not be confirmed."));
      }
    }

    void verifyEmail();

    return () => {
      isMounted = false;
    };
  }, [pick, token]);

  const isSuccess = status === "success";
  const isError = status === "error";

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <section className="ce-shell-sm flex min-h-screen flex-col justify-center py-10">
        <div className="mb-8 flex items-center justify-between gap-3">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-cyan-200 hover:text-white">
            <ArrowLeft size={16} /> {pick("Pagina principala", "Home")}
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitcher compact />
            <ThemeSwitcher />
          </div>
        </div>

        <div className="ce-panel ce-lifted-shell ce-reveal rounded-2xl p-6 shadow-2xl md:p-8">
          <span className={`flex h-14 w-14 items-center justify-center rounded-2xl ${
            isError ? "bg-red-400/15 text-red-200" : "bg-cyan-300/15 text-cyan-100"
          }`}>
            {isSuccess ? <CheckCircle2 size={28} /> : <MailCheck size={28} />}
          </span>
          <p className="mt-6 text-sm font-black text-cyan-200">
            {pick("Confirmare email", "Email confirmation")}
          </p>
          <h1 className="mt-3 text-4xl font-black">
            {isSuccess
              ? pick("Cont activat.", "Account activated.")
              : isError
                ? pick("Nu am putut confirma emailul.", "We could not confirm the email.")
                : pick("Se verifica linkul.", "Checking the link.")}
          </h1>
          <p className="mt-4 max-w-xl leading-7 text-gray-300">{message}</p>

          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/login"
              className="inline-flex justify-center rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
            >
              {pick("Mergi la login", "Go to login")}
            </Link>
            <Link
              href="/"
              className="inline-flex justify-center rounded-lg border border-white/12 px-5 py-3 font-black text-white hover:bg-white/10"
            >
              {pick("Pagina principala", "Home")}
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}

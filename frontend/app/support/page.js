"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Clock3,
  CreditCard,
  Loader2,
  MessageCircle,
  Send,
  ShieldCheck,
} from "lucide-react";
import { API_URL } from "../config";
import { AppHeader } from "../components/AppHeader";
import { useLocale } from "../components/LocaleProvider";
import { getApiErrorMessage, readApiJson } from "../utils/apiResponse";
import { trackEvent } from "../utils/analytics";

const CONTACT_EMAIL = "contact@cealeg.shop";
const SUPPORT_TOPICS = [
  { value: "account", ro: "Întrebare despre cont", en: "Account question" },
  { value: "payment", ro: "Problemă la plată", en: "Payment issue" },
  { value: "wrong_product", ro: "Produs identificat greșit", en: "Incorrectly identified product" },
  { value: "alternatives", ro: "Alternative nepotrivite", en: "Unsuitable alternatives" },
  { value: "privacy", ro: "Ștergere date sau cont", en: "Delete data or account" },
  { value: "partnership", ro: "Parteneriat", en: "Partnership" },
];

export default function SupportPage() {
  const { pick } = useLocale();
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState("account");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");
  const [statusTone, setStatusTone] = useState("info");
  const [isSending, setIsSending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();

    if (isSending) return;

    setIsSending(true);
    setStatus("");

    try {
      const selectedTopic = SUPPORT_TOPICS.find((item) => item.value === topic);
      const topicLabel = selectedTopic ? pick(selectedTopic.ro, selectedTopic.en) : topic;
      const response = await fetch(`${API_URL}/support/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, topic: topicLabel, message }),
      });
      const data = await readApiJson(response, "Suport");

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(
            data,
            pick,
            "Mesajul nu a putut fi trimis.",
            "The message could not be sent."
          )
        );
      }

      setStatusTone("success");
      setStatus(pick(data.message || "Mesajul a fost trimis.", "Your message was sent."));
      setMessage("");
      trackEvent("support_message", { topic: topicLabel });
    } catch (error) {
      setStatusTone("error");
      setStatus(error.message || pick("Mesajul nu a putut fi trimis.", "The message could not be sent."));
    } finally {
      setIsSending(false);
    }
  }

  const statusClass =
    statusTone === "success"
      ? "border-cyan-300/30 bg-cyan-300/10 text-cyan-100"
      : statusTone === "error"
        ? "border-red-400/30 bg-red-400/10 text-red-100"
        : "border-white/10 bg-white/[0.05] text-gray-200";

  return (
    <main className="min-h-screen text-white">
      <AppHeader />
      <section className="ce-shell ce-page">
        <Link
          href="/"
          className="inline-flex min-h-11 items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
        >
          <ArrowLeft size={16} />
          {pick("Pagina principală", "Home")}
        </Link>

        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-start">
          <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-7 shadow-2xl">
            <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
              <MessageCircle size={18} />
              {pick("Suport", "Support")}
            </p>
            <h1 className="mt-4 text-4xl font-black md:text-5xl">
              {pick("Ai nevoie de ajutor?", "Need help?")}
            </h1>
            <p className="mt-4 max-w-2xl leading-8 text-gray-300">
              {pick(
                "Trimite-ne mesajul tău pentru cont, abonament, plată, scanare, produse identificate greșit sau ștergerea datelor.",
                "Send us a message for account, subscription, payment, scan, incorrect product or data deletion issues."
              )}
            </p>

            <form onSubmit={handleSubmit} className="mt-7 space-y-4" aria-busy={isSending}>
              <div>
                <label htmlFor="support-email" className="text-sm font-black text-gray-200">
                  Email
                </label>
                <input
                  id="support-email"
                  type="email"
                  name="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="email"
                  placeholder="nume@email.ro"
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                />
              </div>

              <div>
                <label htmlFor="support-topic" className="text-sm font-black text-gray-200">
                  {pick("Subiect", "Topic")}
                </label>
                <select
                  id="support-topic"
                  name="topic"
                  value={topic}
                  onChange={(event) => setTopic(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                >
                  {SUPPORT_TOPICS.map((item) => (
                    <option key={item.value} value={item.value}>
                      {pick(item.ro, item.en)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="support-message" className="text-sm font-black text-gray-200">
                  {pick("Mesaj", "Message")}
                </label>
                <textarea
                  id="support-message"
                  name="message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  required
                  minLength={10}
                  rows={6}
                  placeholder={pick(
                    "Scrie ce s-a întâmplat și, dacă poți, include produsul, pagina și emailul contului.",
                    "Tell us what happened and, if possible, include the product, page and account email."
                  )}
                  className="mt-2 w-full resize-y rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
                />
              </div>

              {status && (
                <p
                  className={`rounded-2xl border p-4 text-sm ${statusClass}`}
                  role={statusTone === "error" ? "alert" : "status"}
                  aria-live={statusTone === "error" ? "assertive" : "polite"}
                  aria-atomic="true"
                >
                  {status}
                </p>
              )}

              <button
                type="submit"
                disabled={isSending}
                aria-disabled={isSending}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-5 py-3 font-black text-black transition hover:bg-cyan-100 disabled:cursor-wait disabled:opacity-70 sm:w-auto"
              >
                {isSending ? (
                  <Loader2 size={18} className="animate-spin" aria-hidden="true" />
                ) : (
                  <Send size={18} aria-hidden="true" />
                )}
                {isSending ? pick("Se trimite...", "Sending...") : pick("Trimite mesajul", "Send message")}
              </button>
            </form>

            <p className="mt-5 text-sm text-gray-400">
              {pick("Poți scrie și direct la", "You can also email us directly at")}{" "}
              <a
                href={`mailto:${CONTACT_EMAIL}`}
                className="inline-flex min-h-11 items-center font-bold text-cyan-200 hover:text-white"
              >
                {CONTACT_EMAIL}
              </a>
              .
            </p>
          </div>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
              <Clock3 className="text-cyan-200" />
              <h2 className="mt-4 text-xl font-black">
                {pick("Răspuns cât mai rapid", "Fast response")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                {pick(
                  "Prioritizăm problemele de plată, acces la cont și scanări care dau rezultate greșite.",
                  "We prioritize payment, account access and scan issues that return incorrect results."
                )}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
              <CreditCard className="text-cyan-200" />
              <h2 className="mt-4 text-xl font-black">
                {pick("Abonamente și rambursări", "Subscriptions and refunds")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                {pick(
                  "Abonamentele pot fi administrate sau anulate din portalul Stripe. Dacă plata s-a dublat sau planul nu s-a activat corect, trimite emailul contului și numărul facturii.",
                  "Subscriptions can be managed or cancelled from the Stripe customer portal. If you were charged twice or your plan did not activate correctly, send your account email and invoice number."
                )}
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
              <ShieldCheck className="text-cyan-200" />
              <h2 className="mt-4 text-xl font-black">
                {pick("Date utile", "Useful details")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-gray-400">
                {pick(
                  "Include produsul, magazinul, pagina unde ai văzut problema și o captură de ecran dacă este disponibilă.",
                  "Include the product, store, page where the issue happened and a screenshot if available."
                )}
              </p>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Barcode,
  Clock3,
  Heart,
  ListPlus,
  LogOut,
  ScanLine,
  ShieldCheck,
  ShoppingCart,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import { API_URL } from "../config";
import { AppHeader } from "../components/AppHeader";
import { InlineNotice } from "../components/InlineNotice";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";

const ACTION_TONES = {
  emerald: {
    card: "border-emerald-300/50 bg-emerald-400 text-black hover:bg-emerald-300",
    icon: "bg-black/10 text-black",
    description: "text-black/70",
  },
  cyan: {
    card: "border-cyan-300/20 bg-cyan-300/[0.06] hover:border-cyan-300/45 hover:bg-cyan-300/[0.1]",
    icon: "bg-cyan-300/12 text-cyan-200",
    description: "text-gray-400",
  },
  violet: {
    card: "border-violet-300/20 bg-violet-300/[0.06] hover:border-violet-300/45 hover:bg-violet-300/[0.1]",
    icon: "bg-violet-300/12 text-violet-200",
    description: "text-gray-400",
  },
  amber: {
    card: "border-yellow-300/20 bg-yellow-300/[0.05] hover:border-yellow-300/45 hover:bg-yellow-300/[0.1]",
    icon: "bg-yellow-300/12 text-yellow-200",
    description: "text-gray-400",
  },
};

export default function DashboardPage() {
  const { pick } = useLocale();
  const [user, setUser] = useState(null);
  const [counts, setCounts] = useState({ cart: 0, history: 0, favorites: 0 });
  const [billing, setBilling] = useState(null);
  const [emailStatusNotice, setEmailStatusNotice] = useState("");
  const [deleteRequestNotice, setDeleteRequestNotice] = useState("");
  const [deleteRequestLink, setDeleteRequestLink] = useState("");
  const [deleteRequestError, setDeleteRequestError] = useState("");
  const [isDeleteConfirmVisible, setIsDeleteConfirmVisible] = useState(false);
  const [isDeleteRequesting, setIsDeleteRequesting] = useState(false);
  const [lastScannedProduct, setLastScannedProduct] = useState("-");
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const actions = [
    { href: "/live-assistant", title: pick("Asistent live", "Live assistant"), description: pick("Arata produsul si primesti recomandari dupa preferintele tale.", "Show the product and get recommendations based on your preferences."), icon: ScanLine, tone: "emerald" },
    { href: "/barcode-scan", title: pick("Scanare cod de bare", "Barcode scanner"), description: pick("Identifica rapid produsul direct cu telefonul.", "Identify products quickly with your phone."), icon: Barcode, tone: "cyan" },
    { href: "/store", title: pick("Cauta produs", "Search products"), description: pick("Gaseste un produs dupa nume si magazin.", "Find a product by name and store."), icon: ScanLine, tone: "violet" },
    { href: "/cart", title: pick("Cosul meu", "My cart"), description: pick("Produse grupate pentru urmatoarea cumparatura.", "Products grouped for your next shopping trip."), icon: ShoppingCart, tone: "amber" },
    { href: "/preferences", title: pick("Preferinte", "Preferences"), description: pick("Seteaza cum alegi alternativele.", "Set how alternatives should be chosen."), icon: SlidersHorizontal, tone: "violet" },
    { href: "/history", title: pick("Istoric", "History"), description: pick("Revino la scanarile si analizele recente.", "Return to your recent scans and analyses."), icon: Clock3, tone: "cyan" },
    { href: "/favorites", title: pick("Favorite", "Favorites"), description: pick("Pastreaza alternativele care merita repetate.", "Keep the alternatives worth buying again."), icon: Heart, tone: "amber" },
    { href: "/submit-product", title: pick("Contribuie produs", "Contribute product"), description: pick("Completeaza catalogul cand un produs lipseste.", "Complete the catalog when a product is missing."), icon: ListPlus, tone: "cyan" },
  ];

  const loadDashboardData = useCallback(async (userId) => {
    try {
      const responses = await Promise.all([
        fetch(`${API_URL}/cart/${userId}`),
        fetch(`${API_URL}/history/${userId}`),
        fetch(`${API_URL}/favorites/${userId}`),
        fetch(`${API_URL}/billing/status`),
      ]);
      const [cart, history, favorites, billingData] = await Promise.all(
        responses.map((response) => response.json())
      );

      if (responses.slice(0, 3).some((response) => !response.ok)) {
        throw new Error(pick("Datele nu au putut fi incarcate momentan.", "Your data could not be loaded right now."));
      }

      setCounts({
        cart: cart.reduce((total, item) => total + (item.quantity || 1), 0),
        history: history.length,
        favorites: favorites.length,
      });
      setLastScannedProduct(history[0]?.name || "-");
      if (responses[3].ok) setBilling(billingData);
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setIsLoading(false);
    }
  }, [pick]);

  useEffect(() => {
    queueMicrotask(async () => {
      const response = await fetch(`${API_URL}/auth/me`);
      if (!response.ok) {
        localStorage.removeItem("cealeg_user");
        window.location.assign("/login");
        return;
      }
      const data = await response.json();
      localStorage.setItem("cealeg_user", JSON.stringify(data.user));
      setUser(data.user);

      const savedEmailStatus = localStorage.getItem("cealeg_email_status");

      if (savedEmailStatus) {
        localStorage.removeItem("cealeg_email_status");
        let emailStatus = null;

        try {
          emailStatus = JSON.parse(savedEmailStatus);
        } catch {
          emailStatus = null;
        }

        if (emailStatus && !emailStatus.welcomeSent) {
          setEmailStatusNotice(
            emailStatus.configured
              ? pick(
                  "Contul este creat, dar emailul de bun venit nu a putut fi trimis momentan.",
                  "The account is ready, but the welcome email could not be sent right now."
                )
              : pick(
                  "Contul este creat. Emailurile nu sunt conectate inca pe server.",
                  "The account is ready. Email delivery is not connected on the server yet."
                )
          );
        }
      }

      loadDashboardData(data.user.id);
    });
  }, [loadDashboardData, pick]);

  async function logout() {
    await fetch(`${API_URL}/logout`, { method: "POST" }).catch(() => null);
    localStorage.removeItem("cealeg_user");
    window.location.assign("/");
  }

  async function requestAccountDeletion() {
    setIsDeleteRequesting(true);
    setDeleteRequestError("");
    setDeleteRequestNotice("");
    setDeleteRequestLink("");

    try {
      const response = await fetch(`${API_URL}/account/delete/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || pick("Emailul de confirmare nu a putut fi trimis.", "The confirmation email could not be sent."));
      }

      setDeleteRequestNotice(
        data.sent
          ? pick(
              `Am trimis confirmarea la ${data.email}. Contul nu se sterge pana nu confirmi din email.`,
              `We sent the confirmation to ${data.email}. The account is not deleted until you confirm by email.`
            )
          : data.message || pick("Foloseste linkul local de test pentru confirmare.", "Use the local test link to confirm.")
      );

      if (data.devDeletionLink) {
        setDeleteRequestLink(data.devDeletionLink);
      }

      setIsDeleteConfirmVisible(false);
    } catch (error) {
      setDeleteRequestError(error.message || pick("A aparut o eroare.", "An error occurred."));
    } finally {
      setIsDeleteRequesting(false);
    }
  }

  if (!user || isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300">{pick("Se incarca dashboard-ul...", "Loading dashboard...")}</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader />
      <section className="ce-shell ce-page">
        <div className="mb-8 flex items-center justify-between gap-4">
          <Link href="/" className="inline-flex items-center gap-2 text-sm font-bold text-emerald-300 hover:text-emerald-200">
            <ArrowLeft size={16} /> {pick("Pagina principala", "Home")}
          </Link>
          <button onClick={logout} className="inline-flex items-center gap-2 rounded-lg border border-red-400/30 px-4 py-2.5 text-sm font-semibold text-red-300 hover:bg-red-400/10">
            <LogOut size={16} /> {pick("Deconectare", "Sign out")}
          </button>
        </div>

        <div className="ce-panel ce-lifted-shell ce-reveal p-6 md:p-8">
          <p className="text-sm font-bold text-emerald-300">{pick("Spatiul tau", "Your space")}</p>
          <h1 className="mt-3 text-4xl font-bold md:text-5xl">{pick("Salut", "Hello")}, {user.name}</h1>
          <p className="mt-4 max-w-2xl text-gray-300">
            {pick("Continua cumparaturile sau scaneaza un produs nou pentru recomandari potrivite preferintelor tale.", "Continue shopping or scan a new product for recommendations matched to your preferences.")}
          </p>

          <InlineNotice message={loadError} tone="warning" className="mt-6" />

          <InlineNotice message={emailStatusNotice} tone="info" className="mt-6" />

          {billing?.usage && (
            <div className="mt-6 flex flex-col gap-3 rounded-lg border border-emerald-300/25 bg-emerald-400/10 p-5 text-emerald-100 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-bold uppercase tracking-wide text-emerald-300">{billing.usage.plan}</p>
                <p className="mt-1 text-sm">
                  {billing.usage.isUnlimited
                    ? pick("Ai scanari nelimitate active.", "Unlimited scans are active.")
                    : pick(
                        `Mai ai ${billing.usage.weeklyScansRemaining}/${billing.usage.weeklyScanLimit} scanari gratuite saptamana aceasta.`,
                        `${billing.usage.weeklyScansRemaining}/${billing.usage.weeklyScanLimit} free scans left this week.`
                      )}
                </p>
              </div>
              <Link href="/pricing" className="inline-flex justify-center rounded-lg bg-emerald-400 px-4 py-2.5 text-sm font-black text-black hover:bg-emerald-300">
                {pick("Vezi planurile", "View plans")}
              </Link>
            </div>
          )}

          <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              [pick("Produse in cos", "Cart products"), counts.cart, "ce-stat-emerald", "text-emerald-300"],
              [pick("Scanari salvate", "Saved scans"), counts.history, "ce-stat-cyan", "text-cyan-200"],
              [pick("Favorite", "Favorites"), counts.favorites, "ce-stat-violet", "text-violet-200"],
              [pick("Ultima scanare", "Latest scan"), lastScannedProduct, "ce-stat-amber", "text-yellow-200"],
            ].map(([label, value, tone, valueClass]) => (
              <InteractiveSurface key={label} className={`ce-stat-card ${tone} p-5`}>
                <p className="relative z-10 text-sm font-semibold text-gray-400">{label}</p>
                <p className={`relative z-10 mt-2 truncate text-2xl font-black ${valueClass}`}>{value}</p>
              </InteractiveSurface>
            ))}
          </div>

          <div className="mt-9 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-black text-emerald-300">
                {pick("Actiuni rapide", "Quick actions")}
              </p>
              <h2 className="mt-1 text-2xl font-black">
                {pick("Ce vrei sa faci acum?", "What do you want to do now?")}
              </h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-gray-400">
              {pick(
                "Scaneaza la raft, cauta un produs sau continua lista de cumparaturi.",
                "Scan at the shelf, search for a product or continue your shopping list."
              )}
            </p>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-2 2xl:grid-cols-4">
            {actions.map(({ href, title, description, icon: Icon, tone }) => {
              const selectedTone = ACTION_TONES[tone] || ACTION_TONES.cyan;

              return (
                <InteractiveSurface
                  as={Link}
                  key={href}
                  href={href}
                  className={`group flex items-center gap-4 rounded-lg border p-5 transition hover:-translate-y-0.5 ${selectedTone.card}`}
                >
                  <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg ${selectedTone.icon}`}>
                    <Icon size={23} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-lg font-black">{title}</span>
                    <span className={`mt-1 block text-sm leading-6 ${selectedTone.description}`}>{description}</span>
                  </span>
                  <ArrowRight size={18} className="shrink-0 transition group-hover:translate-x-1" />
                </InteractiveSurface>
              );
            })}
          </div>

          {user.isAdmin && (
            <Link href="/admin" className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-emerald-300 hover:text-emerald-200">
              <ShieldCheck size={16} /> {pick("Deschide administrarea", "Open administration")}
            </Link>
          )}

          <div className="ce-danger-panel mt-8 rounded-2xl border p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <p className="flex items-center gap-2 text-sm font-black text-red-300">
                  <Trash2 size={16} /> {pick("Stergere cont", "Delete account")}
                </p>
                <h2 className="mt-2 text-2xl font-black">{pick("Vrei sa inchizi contul?", "Want to close your account?")}</h2>
                <p className="mt-2 leading-7 text-gray-300">
                  {pick(
                    "Iti trimitem un email de confirmare. Contul, istoricul, cosul, favoritele si contributiile tale se sterg doar dupa confirmarea din email.",
                    "We send a confirmation email. Your account, history, cart, favorites and contributions are deleted only after email confirmation."
                  )}
                </p>
              </div>

              {!isDeleteConfirmVisible ? (
                <button
                  type="button"
                  onClick={() => {
                    setDeleteRequestError("");
                    setDeleteRequestNotice("");
                    setDeleteRequestLink("");
                    setIsDeleteConfirmVisible(true);
                  }}
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-red-400/35 px-5 py-3 font-black text-red-200 hover:bg-red-400/10"
                >
                  <Trash2 size={18} />
                  {pick("Sterge contul", "Delete account")}
                </button>
              ) : (
                <div className="shrink-0 space-y-3 rounded-xl border border-red-400/25 bg-black/25 p-4">
                  <p className="max-w-xs text-sm leading-6 text-red-100">
                    {pick(
                      "Confirmarea vine pe email. Dupa apasare, verifica inboxul.",
                      "The confirmation arrives by email. After pressing, check your inbox."
                    )}
                  </p>
                  <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
                    <button
                      type="button"
                      onClick={requestAccountDeletion}
                      disabled={isDeleteRequesting}
                      className={`rounded-lg px-4 py-3 font-black ${
                        isDeleteRequesting
                          ? "cursor-not-allowed bg-white/10 text-gray-400"
                          : "bg-red-400 text-black hover:bg-red-300"
                      }`}
                    >
                      {isDeleteRequesting ? pick("Se trimite...", "Sending...") : pick("Trimite confirmarea", "Send confirmation")}
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsDeleteConfirmVisible(false)}
                      className="rounded-lg border border-white/10 px-4 py-3 font-bold text-gray-200 hover:bg-white/10"
                    >
                      {pick("Anuleaza", "Cancel")}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {deleteRequestNotice && (
              <div className="mt-4 rounded-lg border border-emerald-300/30 bg-emerald-400/10 p-4 text-sm text-emerald-100">
                {deleteRequestNotice}
                {deleteRequestLink && (
                  <a href={deleteRequestLink} className="mt-3 block font-black text-emerald-300 hover:text-emerald-200">
                    {pick("Deschide linkul local de confirmare", "Open local confirmation link")}
                  </a>
                )}
              </div>
            )}

            {deleteRequestError && (
              <div className="mt-4 rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-200">
                {deleteRequestError}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

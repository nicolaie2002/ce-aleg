"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, CreditCard, Crown, Sparkles, Zap } from "lucide-react";
import { API_URL } from "../config";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { ThemeSwitcher } from "../components/ThemeSwitcher";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";
import { readApiJson } from "../utils/apiResponse";

const fallbackPlans = {
  free: {
    name: "Free",
    monthlyPrice: 0,
    yearlyPrice: 0,
    weeklyScanLimit: 5,
    features: [
      "5 scanari pe saptamana",
      "2 alternative pentru fiecare produs",
      "verdict rapid si istoric de baza",
    ],
  },
  pro: {
    name: "Pro",
    monthlyPrice: 19.99,
    yearlyPrice: 149,
    weeklyScanLimit: null,
    features: [
      "scanari nelimitate",
      "3 alternative imediat + afiseaza mai multe",
      "cautare dupa preferintele tale",
      "istoric complet",
    ],
  },
  family: {
    name: "Family",
    monthlyPrice: 29.99,
    yearlyPrice: 249,
    weeklyScanLimit: null,
    features: [
      "scanari nelimitate",
      "profiluri pentru familie",
      "liste comune de cumparaturi",
    ],
  },
};

const featureLabels = {
  "5 scanari pe saptamana": {
    ro: "5 scanări pe săptămână",
    en: "5 scans per week",
  },
  "2 alternative pentru fiecare produs": {
    ro: "2 alternative pentru fiecare produs",
    en: "2 alternatives for each product",
  },
  "verdict rapid si istoric de baza": {
    ro: "verdict rapid și istoric de bază",
    en: "quick verdict and basic history",
  },
  "scanari nelimitate": {
    ro: "scanări nelimitate",
    en: "unlimited scans",
  },
  "asistent live la raft": {
    ro: "AI preview in dezvoltare",
    en: "AI preview in development",
  },
  "asistent smart live": {
    ro: "AI preview in dezvoltare",
    en: "AI preview in development",
  },
  "AI preview in dezvoltare": {
    ro: "AI preview în dezvoltare",
    en: "AI preview in development",
  },
  "3 alternative imediat + afiseaza mai multe": {
    ro: "3 alternative imediat + afișează mai multe",
    en: "3 instant alternatives + show more",
  },
  "cautare dupa preferintele tale": {
    ro: "căutare după preferințele tale",
    en: "search by your preferences",
  },
  "istoric complet": {
    ro: "istoric complet",
    en: "full history",
  },
  "mai multe alternative": {
    ro: "mai multe alternative",
    en: "more alternatives",
  },
  "profiluri pentru familie": {
    ro: "profiluri pentru familie",
    en: "family profiles",
  },
  "preferinte separate": {
    ro: "preferințe separate",
    en: "separate preferences",
  },
  "liste comune de cumparaturi": {
    ro: "liste comune de cumpărături",
    en: "shared shopping lists",
  },
};

function getFeatureLabel(feature, locale) {
  return featureLabels[feature]?.[locale] || feature;
}

function PlanCard({ id, plan, currentPlan, billingCycle, onChoose, pick, busyPlan }) {
  const isCurrent = currentPlan === id;
  const isFree = id === "free";
  const isPro = id === "pro";
  const isYearly = billingCycle === "yearly";
  const isBusy = busyPlan === `${id}:${billingCycle}`;
  const displayPrice = isYearly ? plan.yearlyPrice : plan.monthlyPrice;
  const priceSuffix = isYearly ? pick("/ an", "/ year") : pick("/ lună", "/ month");
  const monthlyEquivalent =
    isYearly && !isFree ? Number(plan.yearlyPrice || 0) / 12 : null;

  return (
    <InteractiveSurface
      as="article"
      className={`ce-plan-card ce-plan-${id} ${
        isCurrent ? "ce-plan-current" : ""
      } relative flex h-full min-h-[438px] flex-col overflow-hidden rounded-2xl border p-6 shadow-2xl transition hover:-translate-y-1`}
    >
      <div className="flex min-h-9 items-start justify-between gap-3">
        <h2 className="text-2xl font-black">{plan.name}</h2>
        <div className="flex shrink-0 items-center gap-2">
          {isPro && !isCurrent && (
            <span className="rounded-full bg-yellow-300 px-3 py-1 text-xs font-black text-black shadow-[0_0_20px_rgba(250,204,21,.22)]">
              {pick("Recomandat", "Popular")}
            </span>
          )}
          {!isFree && (
            <Crown size={21} className={isCurrent ? "text-cyan-200" : "text-yellow-300"} />
          )}
        </div>
      </div>

      <p className="mt-5 text-4xl font-black">
        {Number(displayPrice || 0).toFixed(displayPrice ? 2 : 0)} lei
        <span className={`text-sm font-semibold ${isCurrent ? "text-cyan-100/70" : "text-gray-400"}`}>
          {" "}
          {priceSuffix}
        </span>
      </p>
      {!isFree && (
        <p className={`mt-1 text-sm ${isCurrent ? "text-cyan-100/70" : "text-gray-400"}`}>
          {isYearly
            ? pick(
                `aprox. ${monthlyEquivalent.toFixed(2)} lei / lună`,
                `about ${monthlyEquivalent.toFixed(2)} lei / month`
              )
            : pick(`${plan.yearlyPrice} lei / an`, `${plan.yearlyPrice} lei / year`)}
        </p>
      )}

      <ul className="mt-6 flex-1 space-y-3">
        {(plan.features || []).map((feature) => (
          <li key={feature} className="flex gap-2 text-sm">
            <Check size={16} className="mt-0.5 shrink-0" />
            <span>{getFeatureLabel(feature, pick("ro", "en"))}</span>
          </li>
        ))}
      </ul>

      <button
        onClick={() => onChoose(id, billingCycle)}
        disabled={isCurrent || isBusy}
        className={`mt-7 w-full rounded-lg px-4 py-3 font-black transition ${
          isCurrent
            ? "cursor-default border border-white/15 bg-black text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
            : isBusy
              ? "cursor-wait bg-white/10 text-gray-400"
            : isFree
              ? "border border-white/15 text-white hover:bg-white/10"
              : "bg-white text-black shadow-[0_0_26px_rgba(103,232,249,0.16)] hover:bg-cyan-100"
        }`}
      >
        {isBusy
          ? pick("Se deschide plata...", "Opening checkout...")
          : isCurrent
          ? pick("Planul tau actual", "Current plan")
          : isFree
            ? pick("Ramai pe Free", "Stay on Free")
            : isYearly
              ? pick("Alege anual", "Choose yearly")
              : pick("Alege lunar", "Choose monthly")}
      </button>
    </InteractiveSurface>
  );
}

export default function PricingPage() {
  const { pick } = useLocale();
  const [billing, setBilling] = useState(null);
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState("info");
  const [busyPlan, setBusyPlan] = useState("");
  const [isOpeningPortal, setIsOpeningPortal] = useState(false);
  const [billingCycle, setBillingCycle] = useState("monthly");
  const plans = billing?.plans || fallbackPlans;
  const currentPlan = billing?.usage?.plan || "free";
  const subscription = billing?.subscription;
  const canManageBilling =
    subscription?.provider === "stripe" && subscription?.hasCustomer;

  function loadBillingStatus({ syncStripe = false } = {}) {
    const syncQuery = syncStripe ? "?sync=stripe" : "";
    return fetch(`${API_URL}/billing/status${syncQuery}`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => setBilling(data))
      .catch(() => setBilling(null));
  }

  useEffect(() => {
    loadBillingStatus({ syncStripe: true });
  }, []);

  useEffect(() => {
    const checkoutStatus = new URLSearchParams(window.location.search).get("checkout");
    let nextTone = "";
    let nextMessage = "";

    if (checkoutStatus === "success") {
      nextTone = "success";
      nextMessage = pick(
        "Plata a fost confirmată. Planul se actualizează automat imediat ce Stripe trimite confirmarea.",
        "Payment confirmed. Your plan updates automatically as soon as Stripe sends the confirmation."
      );
    }

    if (checkoutStatus === "cancelled") {
      nextTone = "info";
      nextMessage = pick(
        "Plata a fost anulată. Poți alege planul oricând ești pregătit.",
        "Payment was cancelled. You can choose a plan whenever you are ready."
      );
    }

    if (nextMessage) {
      window.history.replaceState(null, "", "/pricing");
      queueMicrotask(() => {
        setMessageTone(nextTone);
        setMessage(nextMessage);
        if (checkoutStatus === "success") {
          loadBillingStatus({ syncStripe: true });
        }
      });
    }
  }, [pick]);

  async function choosePlan(plan, selectedBillingCycle = billingCycle) {
    if (plan === "free") return;

    setBusyPlan(`${plan}:${selectedBillingCycle}`);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan, billingInterval: selectedBillingCycle }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(
          data.error ||
            pick(
              "Plata nu poate fi pornită momentan.",
              "Checkout cannot start right now."
            )
        );
      }

      if (data.checkoutUrl) {
        window.location.assign(data.checkoutUrl);
        return;
      }

      if (data.updated) {
        setMessageTone("success");
        setMessage(
          data.message ||
            pick(
              "Abonamentul a fost actualizat.",
              "Your subscription was updated."
            )
        );
        loadBillingStatus({ syncStripe: true });
        return;
      }

      setMessageTone("info");
      setMessage(
        data.message ||
          pick(
            "Am notat alegerea ta. Verifica datele de plata sau contacteaza-ne pentru activare.",
            "We saved your choice. Check payment settings or contact us for activation."
          )
      );
    } catch (error) {
      setMessageTone("error");
      setMessage(
        error.message ||
          pick("A aparut o eroare la plata.", "A payment error occurred.")
      );
    } finally {
      setBusyPlan("");
    }
  }

  async function openBillingPortal() {
    setIsOpeningPortal(true);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/billing/portal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await readApiJson(response);

      if (!response.ok || !data.portalUrl) {
        throw new Error(
          data.error ||
            pick(
              "Portalul de abonament nu poate fi deschis momentan.",
              "The billing portal cannot be opened right now."
            )
        );
      }

      window.location.assign(data.portalUrl);
    } catch (error) {
      setMessageTone("error");
      setMessage(
        error.message ||
          pick("Nu am putut deschide abonamentul.", "We could not open billing.")
      );
    } finally {
      setIsOpeningPortal(false);
    }
  }

  return (
    <main className="min-h-screen text-white">
      <section className="ce-shell ce-page">
        <div className="flex items-center justify-between gap-4">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white"
          >
            <ArrowLeft size={16} /> {pick("Înapoi la dashboard", "Back to dashboard")}
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitcher compact />
            <ThemeSwitcher />
          </div>
        </div>

        <div className="mt-10 grid gap-8 xl:grid-cols-[minmax(0,1fr)_520px] xl:items-end">
          <div className="max-w-4xl">
            <p className="flex items-center gap-2 text-sm font-bold text-cyan-200">
              <Sparkles size={16} /> {pick("Planuri", "Plans")}
            </p>
            <h1 className="mt-3 text-5xl font-black leading-tight md:text-6xl">
              {pick(
                "Alege mai bine la fiecare cumpărătură.",
                "Choose better on every shopping trip."
              )}
            </h1>
            <p className="mt-5 text-lg leading-8 text-gray-300">
              {pick(
                "Scanezi produsul, vezi verdictul și primești alternative clare. Free e perfect pentru început. Pro deblochează căutarea după preferințe și mai multe recomandări.",
                "Scan a product, see the verdict and get clear alternatives. Free is great to start. Pro unlocks preference search and more recommendations."
              )}
            </p>
          </div>

          <div className="ce-pricing-note rounded-2xl border p-5 shadow-2xl backdrop-blur">
            <div className="flex items-start gap-3">
              <span className="rounded-lg bg-cyan-200 p-2 text-black">
                <Zap size={20} />
              </span>
              <div>
                <p className="font-black">
                  {pick("Simplu pentru cumparator", "Simple for shoppers")}
                </p>
                <p className="mt-2 text-sm leading-6 text-gray-300">
                  {pick(
                    "Free arată primele recomandări bune. Pro te lasă să ceri exact ce cauți: mai ieftin, fără zahăr, mai multă proteină sau ingrediente mai curate.",
                    "Free shows the first good picks. Pro lets you ask for exactly what you want: cheaper, less sugar, more protein or cleaner ingredients."
                  )}
                </p>
              </div>
            </div>
            {canManageBilling && (
              <button
                type="button"
                onClick={openBillingPortal}
                disabled={isOpeningPortal}
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 font-black text-white hover:bg-white/10 disabled:cursor-wait disabled:text-gray-400"
              >
                <CreditCard size={18} />
                {isOpeningPortal
                  ? pick("Se deschide...", "Opening...")
                  : pick("Administrează abonamentul", "Manage subscription")}
              </button>
            )}
          </div>
        </div>

        {billing?.usage && (
          <div className="ce-usage-banner mt-7 rounded-lg border p-5">
            {billing.usage.isUnlimited
              ? pick("Ai scanări nelimitate active.", "Unlimited scans are active.")
              : pick(
                  `Ai folosit ${billing.usage.weeklyScansUsed}/${billing.usage.weeklyScanLimit} scanări gratuite săptămâna aceasta.`,
                  `You used ${billing.usage.weeklyScansUsed}/${billing.usage.weeklyScanLimit} free scans this week.`
                )}
          </div>
        )}

        {message && (
          <p
            className={`mt-5 rounded-lg border p-4 ${
              messageTone === "success"
                ? "border-cyan-300/25 bg-cyan-300/10 text-cyan-100"
                : messageTone === "error"
                  ? "border-red-400/30 bg-red-400/10 text-red-200"
                  : "border-yellow-300/25 bg-yellow-300/10 text-yellow-100"
            }`}
          >
            {message}
          </p>
        )}

        <div className="mt-8 flex flex-col gap-3 rounded-2xl border border-white/10 bg-black/25 p-3 sm:inline-flex sm:flex-row sm:items-center">
          <span className="px-3 text-sm font-bold text-gray-300">
            {pick("Alege perioada", "Choose billing")}
          </span>
          <div className="grid grid-cols-2 gap-2 rounded-xl bg-black/30 p-1">
            {[
              { id: "monthly", label: pick("Lunar", "Monthly") },
              { id: "yearly", label: pick("Anual", "Yearly") },
            ].map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setBillingCycle(option.id)}
                className={`rounded-lg px-4 py-2 text-sm font-black transition ${
                  billingCycle === option.id
                    ? "bg-white text-black"
                    : "text-gray-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <span className="px-3 text-sm text-cyan-100">
            {billingCycle === "yearly"
              ? pick("Platesti o data pe an.", "Pay once per year.")
              : pick("Plătești lunar.", "Pay monthly.")}
          </span>
        </div>

        <div className="mt-8 grid gap-5 md:grid-cols-3 xl:gap-8">
          {["free", "pro", "family"].map((id) => (
            <PlanCard
              key={id}
              id={id}
              plan={plans[id]}
              currentPlan={currentPlan}
              billingCycle={billingCycle}
              onChoose={choosePlan}
              pick={pick}
              busyPlan={busyPlan}
            />
          ))}
        </div>
      </section>
    </main>
  );
}

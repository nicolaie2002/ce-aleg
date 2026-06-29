"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
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
    monthlyScanLimit: 5,
    weeklyScanLimit: 5,
    features: [
      "5 scanari pe luna",
      "2 alternative pentru fiecare produs",
      "scanare cod de bare si cautare manuala",
      "verdict rapid",
      "istoric de baza",
    ],
  },
  pro: {
    name: "Pro",
    monthlyPrice: 19.99,
    yearlyPrice: 149,
    weeklyScanLimit: null,
    features: [
      "scanari nelimitate",
      "3 alternative initiale plus afiseaza mai multe",
      "cautare dupa preferintele tale",
      "istoric complet",
      "cos si favorite salvate",
      "asistent vizual AI in curand",
    ],
  },
  family: {
    name: "Family",
    monthlyPrice: 29.99,
    yearlyPrice: 249,
    weeklyScanLimit: null,
    features: [
      "scanari nelimitate",
      "3 alternative initiale plus afiseaza mai multe",
      "cautare dupa preferintele tale",
      "istoric complet",
      "cos si favorite salvate",
      "profiluri pentru familie",
      "preferinte separate pe profil",
      "cos separat pentru fiecare profil",
      "asistent vizual AI in curand",
    ],
  },
};

const fallbackCoinPacks = [
  {
    id: "bronze",
    title: "Bronze CeCoins",
    coins: 500,
    priceText: "9,99 lei",
    configured: false,
    image: "/brand/Bronze.png",
    icon: "/brand/Bronze_icon.png",
    descriptionRo: "Pentru cateva scanari bonus si recompense rapide.",
    descriptionEn: "For a few bonus scans and quick rewards.",
  },
  {
    id: "gold",
    title: "Gold CeCoins",
    coins: 1200,
    priceText: "19,99 lei",
    configured: false,
    image: "/brand/Gold.png",
    icon: "/brand/Gold_icon.png",
    descriptionRo: "Mai multe puncte pentru saptamanile cu multe cumparaturi.",
    descriptionEn: "More points for weeks with heavier shopping.",
  },
  {
    id: "diamond",
    title: "Diamond CeCoins",
    coins: 3000,
    priceText: "39,99 lei",
    configured: false,
    image: "/brand/Diamond.png",
    icon: "/brand/Diamond_icon.png",
    descriptionRo: "Cel mai bun pachet pentru scanari bonus si activari dese.",
    descriptionEn: "The best pack for bonus scans and frequent unlocks.",
  },
];

const CECOIN_PACK_VISUALS = {
  bronze: { image: "/brand/Bronze.png", icon: "/brand/Bronze_icon.png" },
  gold: { image: "/brand/Gold.png", icon: "/brand/Gold_icon.png" },
  diamond: { image: "/brand/Diamond.png", icon: "/brand/Diamond_icon.png" },
};

const featureLabels = {
  "5 scanari pe luna": {
    ro: "5 scanări pe lună",
    en: "5 scans per month",
  },
  "5 scanari pe saptamana": {
    ro: "5 scanări pe lună",
    en: "5 scans per month",
  },
  "2 alternative pentru fiecare produs": {
    ro: "2 alternative pentru fiecare produs",
    en: "2 alternatives for each product",
  },
  "scanare cod de bare si cautare manuala": {
    ro: "scanare cod de bare și căutare manuală",
    en: "barcode scanning and manual search",
  },
  "verdict rapid": {
    ro: "verdict rapid pentru produs",
    en: "quick product verdict",
  },
  "istoric de baza": {
    ro: "istoric de bază",
    en: "basic history",
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
    ro: "asistent vizual AI în curând",
    en: "AI visual assistant coming soon",
  },
  "asistent smart live": {
    ro: "asistent vizual AI în curând",
    en: "AI visual assistant coming soon",
  },
  "asistent live Pro": {
    ro: "asistent vizual AI în curând",
    en: "AI visual assistant coming soon",
  },
  "asistent vizual AI in curand": {
    ro: "asistent vizual AI în curând",
    en: "AI visual assistant coming soon",
  },
  "3 alternative initiale plus afiseaza mai multe": {
    ro: "3 alternative inițiale + afișează mai multe",
    en: "3 instant alternatives + show more",
  },
  "3 alternative imediat + afiseaza mai multe": {
    ro: "3 alternative inițiale + afișează mai multe",
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
  "cos si favorite salvate": {
    ro: "coș și favorite salvate",
    en: "saved cart and favorites",
  },
  "mai multe alternative": {
    ro: "mai multe alternative",
    en: "more alternatives",
  },
  "tot ce include Pro": {
    ro: "tot ce include Pro",
    en: "everything included in Pro",
  },
  "profiluri pentru familie": {
    ro: "profiluri pentru familie",
    en: "family profiles",
  },
  "preferinte separate pe profil": {
    ro: "preferințe separate pe profil",
    en: "separate preferences per profile",
  },
  "cos separat pentru fiecare profil": {
    ro: "coș separat pentru fiecare profil",
    en: "separate cart for each profile",
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

function formatBillingDate(dateString, locale) {
  if (!dateString) return "";

  try {
    return new Intl.DateTimeFormat(locale === "en" ? "en-GB" : "ro-RO", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    }).format(new Date(dateString));
  } catch {
    return "";
  }
}

function PlanCard({
  id,
  plan,
  currentPlan,
  billingCycle,
  onChoose,
  pick,
  busyPlan,
  isLockedByActiveSubscription,
  lockedUntilLabel,
}) {
  const isCurrent = currentPlan === id;
  const isFree = id === "free";
  const isPro = id === "pro";
  const isYearly = billingCycle === "yearly";
  const isBusy = busyPlan === `${id}:${billingCycle}`;
  const isLocked = isLockedByActiveSubscription && !isCurrent;
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
        disabled={isCurrent || isBusy || isLocked}
        className={`mt-7 w-full rounded-lg px-4 py-3 font-black transition ${
          isCurrent
            ? "cursor-default border border-white/15 bg-black text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
            : isLocked
              ? "cursor-not-allowed border border-white/10 bg-white/5 text-gray-400"
            : isBusy
              ? "cursor-wait bg-white/10 text-gray-400"
            : isFree
              ? "border border-white/15 text-white hover:bg-white/10"
              : "bg-white text-black shadow-[0_0_26px_rgba(103,232,249,0.16)] hover:bg-cyan-100"
        }`}
      >
        {isBusy
          ? pick("Se deschide plata...", "Opening checkout...")
          : isLocked
          ? lockedUntilLabel
            ? pick(`Disponibil după ${lockedUntilLabel}`, `Available after ${lockedUntilLabel}`)
            : pick("Disponibil după expirare", "Available after expiry")
          : isCurrent
          ? pick("Planul tău actual", "Current plan")
          : isFree
            ? pick("Rămâi pe Free", "Stay on Free")
            : isYearly
              ? pick("Alege anual", "Choose yearly")
              : pick("Alege lunar", "Choose monthly")}
      </button>
    </InteractiveSurface>
  );
}

export default function PricingPage() {
  const { pick, locale } = useLocale();
  const [billing, setBilling] = useState(null);
  const [message, setMessage] = useState("");
  const [messageTone, setMessageTone] = useState("info");
  const [busyPlan, setBusyPlan] = useState("");
  const [coinPacks, setCoinPacks] = useState(fallbackCoinPacks);
  const [busyCoinPack, setBusyCoinPack] = useState("");
  const [coinPackMessage, setCoinPackMessage] = useState("");
  const [isOpeningPortal, setIsOpeningPortal] = useState(false);
  const [billingCycle, setBillingCycle] = useState("monthly");
  const plans = billing?.plans || fallbackPlans;
  const currentPlan = billing?.usage?.plan || "free";
  const subscription = billing?.subscription;
  const subscriptionEndLabel = formatBillingDate(subscription?.currentPeriodEnd, locale);
  const hasActivePaidSubscription =
    ["pro", "family"].includes(currentPlan) &&
    ["active", "trialing", "past_due"].includes(subscription?.status) &&
    (!subscription?.currentPeriodEnd || new Date(subscription.currentPeriodEnd) > new Date());
  const currentPlanName = plans[currentPlan]?.name || currentPlan;
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
    let isMounted = true;

    fetch(`${API_URL}/gamification/coin-packs`)
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (isMounted && response.ok && data.coinPacks?.length) {
          setCoinPacks(
            data.coinPacks.map((pack) => ({
              ...pack,
              descriptionRo:
                fallbackCoinPacks.find((fallbackPack) => fallbackPack.id === pack.id)?.descriptionRo ||
                "CeCoins pentru bonusuri si activari in aplicatie.",
              descriptionEn:
                fallbackCoinPacks.find((fallbackPack) => fallbackPack.id === pack.id)?.descriptionEn ||
                "CeCoins for bonuses and in-app unlocks.",
            }))
          );
        }
      })
      .catch(() => null);

    return () => {
      isMounted = false;
    };
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
        if (data.code === "active_subscription_exists") {
          setMessageTone("info");
          setMessage(data.error);
          loadBillingStatus({ syncStripe: true });
          return;
        }

        throw new Error(
          data.error ||
            pick(
              "Plata nu poate fi pornită acum.",
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
            "Am notat alegerea ta. Verifică datele de plată sau contactează-ne pentru activare.",
            "We saved your choice. Check payment settings or contact us for activation."
          )
      );
    } catch (error) {
      setMessageTone("error");
      setMessage(
        error.message ||
          pick("A apărut o eroare la plată.", "A payment error occurred.")
      );
    } finally {
      setBusyPlan("");
    }
  }

  async function buyCoinPack(packId) {
    if (!packId || busyCoinPack) return;

    setBusyCoinPack(packId);
    setCoinPackMessage("");

    try {
      const response = await fetch(`${API_URL}/gamification/coin-checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ packId }),
      });
      const data = await readApiJson(response);

      if (response.status === 401 || response.status === 403) {
        window.location.assign("/login?next=/pricing");
        return;
      }

      if (!response.ok) {
        throw new Error(
          data.error ||
            pick(
              "Pachetul CeCoins nu poate fi cumpărat acum.",
              "This CeCoins pack cannot be purchased right now."
            )
        );
      }

      if (data.checkoutUrl) {
        window.location.assign(data.checkoutUrl);
        return;
      }

      throw new Error(
        pick(
          "Stripe nu a trimis linkul de plată.",
          "Stripe did not return a payment link."
        )
      );
    } catch (error) {
      setCoinPackMessage(
        error.message ||
          pick(
            "Cumpărarea de CeCoins nu poate fi pornită acum.",
            "CeCoins checkout cannot start right now."
          )
      );
    } finally {
      setBusyCoinPack("");
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
              "Portalul de abonament nu poate fi deschis acum.",
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
                "Scanezi produsul, vezi verdictul și primești alternative clare. Free acoperă primele verificări, Pro deblochează recomandări nelimitate și căutare după preferințe, iar Family adaugă profiluri separate pentru casă.",
                "Scan a product, see the verdict and get clear alternatives. Free covers the first checks, Pro unlocks unlimited recommendations and preference search, while Family adds separate household profiles."
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
                  {pick("Simplu pentru cumpărător", "Simple for shoppers")}
                </p>
                <p className="mt-2 text-sm leading-6 text-gray-300">
                  {pick(
                    "Alegi lunar sau anual. Identificarea vizuală cu AI vine în curând pentru Pro și Family.",
                    "Choose monthly or yearly. AI visual identification is coming soon for Pro and Family."
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
              ? subscriptionEndLabel
                ? pick(
                    `Planul ${currentPlanName} este activ până la ${subscriptionEndLabel}.`,
                    `${currentPlanName} is active until ${subscriptionEndLabel}.`
                  )
                : pick(
                    `Planul ${currentPlanName} este activ.`,
                    `${currentPlanName} is active.`
                  )
              : pick(
                  `Ai folosit ${billing.usage.monthlyScansUsed ?? billing.usage.weeklyScansUsed}/${billing.usage.monthlyScanLimit ?? billing.usage.weeklyScanLimit} scanări gratuite luna aceasta.`,
                  `You used ${billing.usage.monthlyScansUsed ?? billing.usage.weeklyScansUsed}/${billing.usage.monthlyScanLimit ?? billing.usage.weeklyScanLimit} free scans this month.`
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
              ? pick("Plătești o dată pe an.", "Pay once per year.")
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
              isLockedByActiveSubscription={hasActivePaidSubscription}
              lockedUntilLabel={subscriptionEndLabel}
            />
          ))}
        </div>

        <section className="mt-10 rounded-2xl border border-cyan-300/20 bg-black/30 p-5 shadow-2xl backdrop-blur md:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-black text-cyan-200">
                <Image
                  src="/brand/CeCoin.png"
                  alt=""
                  width={28}
                  height={28}
                  className="rounded-full"
                />
                {pick("CeCoins", "CeCoins")}
              </p>
              <h2 className="mt-3 text-3xl font-black">
                {pick("Cumpără CeCoins pentru bonusuri rapide.", "Buy CeCoins for quick bonuses.")}
              </h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-300">
                {pick(
                  "Folosești CeCoins pentru scanări bonus și activări temporare în magazinul de recompense. Abonamentele rămân cea mai bună opțiune pentru utilizare constantă.",
                  "Use CeCoins for bonus scans and temporary unlocks in the rewards shop. Subscriptions remain the best option for regular use."
                )}
              </p>
            </div>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center rounded-lg border border-white/15 px-4 py-3 text-sm font-black text-white hover:bg-white/10"
            >
              {pick("Vezi soldul în dashboard", "See balance in dashboard")}
            </Link>
          </div>

          {coinPackMessage && (
            <p className="mt-4 rounded-lg border border-yellow-300/25 bg-yellow-300/10 p-3 text-sm font-bold text-yellow-100">
              {coinPackMessage}
            </p>
          )}

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {coinPacks.map((pack) => (
              <InteractiveSurface
                key={pack.id}
                className="flex h-full flex-col overflow-hidden rounded-xl border border-white/10 bg-white/[0.045] p-5 shadow-xl"
              >
                {(() => {
                  const packVisual = CECOIN_PACK_VISUALS[pack.id] || {};
                  const packImage = pack.image || packVisual.image || "/brand/CeCoin.png";

                  return (
                    <>
                      <div className="mb-5 flex h-36 items-center justify-center rounded-xl border border-white/10 bg-black/25 p-3">
                        <Image
                          src={packImage}
                          alt=""
                          width={220}
                          height={220}
                          className="h-full w-full object-contain drop-shadow-[0_16px_30px_rgba(0,0,0,.42)]"
                          sizes="(min-width: 768px) 28vw, 90vw"
                        />
                      </div>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <Image
                            src={pack.icon || packVisual.icon || "/brand/CeCoin.png"}
                            alt=""
                            width={42}
                            height={42}
                            className="rounded-full shadow-[0_0_24px_rgba(250,204,21,.18)]"
                          />
                          <div>
                            <h3 className="text-lg font-black">{pack.title}</h3>
                            <p className="text-sm font-bold text-yellow-100">{pack.coins} CeCoins</p>
                          </div>
                        </div>
                        <span className="rounded-full border border-yellow-300/25 bg-yellow-300/10 px-3 py-1 text-xs font-black text-yellow-100">
                          {pack.priceText}
                        </span>
                      </div>
                    </>
                  );
                })()}
                <p className="mt-4 flex-1 text-sm leading-6 text-gray-300">
                  {pick(pack.descriptionRo, pack.descriptionEn)}
                </p>
                <button
                  type="button"
                  onClick={() => buyCoinPack(pack.id)}
                  disabled={!pack.configured || busyCoinPack === pack.id}
                  className="mt-5 rounded-lg bg-white px-4 py-3 font-black text-black transition hover:bg-yellow-100 disabled:cursor-not-allowed disabled:bg-white/10 disabled:text-gray-400"
                >
                  {busyCoinPack === pack.id
                    ? pick("Se deschide plata...", "Opening checkout...")
                    : pack.configured
                      ? pick("Cumpără acum", "Buy now")
                      : pick("În curând", "Coming soon")}
                </button>
              </InteractiveSurface>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

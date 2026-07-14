"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowLeft,
  ArrowRight,
  Barcode,
  Clock3,
  Coins,
  Copy,
  Database,
  Eye,
  EyeOff,
  Gift,
  Heart,
  ListPlus,
  LogOut,
  Plus,
  ScanLine,
  ShieldCheck,
  ShoppingCart,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Trophy,
} from "lucide-react";
import { API_URL } from "../config";
import { AppHeader } from "../components/AppHeader";
import { InlineNotice } from "../components/InlineNotice";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";
import { getActiveProfile } from "../utils/profilePreferences";
import { getApiErrorMessage, readApiJson } from "../utils/apiResponse";
import { trackEvent } from "../utils/analytics";

const ACTION_TONES = {
  emerald: {
    card: "border-cyan-300/35 bg-white text-black hover:bg-cyan-100",
    icon: "bg-cyan-200/40 text-black",
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

const CECOIN_PACK_VISUALS = {
  bronze: { image: "/brand/Bronze.webp", icon: "/brand/Bronze_icon.webp" },
  gold: { image: "/brand/Gold.webp", icon: "/brand/Gold_icon.webp" },
  diamond: { image: "/brand/Diamond.webp", icon: "/brand/Diamond_icon.webp" },
};

const FamilyProfiles = dynamic(
  () => import("../components/FamilyProfiles").then((mod) => mod.FamilyProfiles),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-5 text-sm font-bold text-gray-300">
        Se încarcă profilurile familiei...
      </div>
    ),
  }
);

const CECOIN_ASSET_REPLACEMENTS = {
  "/brand/Bronze.png": "/brand/Bronze.webp",
  "/brand/Gold.png": "/brand/Gold.webp",
  "/brand/Diamond.png": "/brand/Diamond.webp",
  "/brand/Bronze_icon.png": "/brand/Bronze_icon.webp",
  "/brand/Gold_icon.png": "/brand/Gold_icon.webp",
  "/brand/Diamond_icon.png": "/brand/Diamond_icon.webp",
  "/brand/CeCoin.png": "/brand/CeCoin.webp",
};

function normalizeCecoinAsset(src, fallback = "/brand/CeCoin.webp") {
  if (!src) return fallback;
  return CECOIN_ASSET_REPLACEMENTS[src] || src;
}

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
  const [isInviteVisible, setIsInviteVisible] = useState(false);
  const [inviteCopyNotice, setInviteCopyNotice] = useState("");
  const [gamification, setGamification] = useState(null);
  const [isGamificationLoading, setIsGamificationLoading] = useState(false);
  const [gamificationError, setGamificationError] = useState("");
  const [buyingPackId, setBuyingPackId] = useState("");
  const [shopMessage, setShopMessage] = useState("");

  const actions = [
    { href: "/barcode-scan", title: pick("Scanează codul", "Scan barcode"), description: pick("Identifică rapid produsul cu telefonul și vezi verdictul.", "Identify the product quickly with your phone and see the verdict."), icon: Barcode, tone: "emerald" },
    { href: "/store", title: pick("Caută produs", "Search products"), description: pick("Găsește produse în catalog după nume și magazin.", "Find products in the catalog by name and store."), icon: ScanLine, tone: "cyan" },
    { href: "/catalog-romania", title: pick("Catalog România", "Romania catalog"), description: pick("Vezi acoperirea catalogului și unde lipsesc produse.", "See catalog coverage and where products are missing."), icon: Database, tone: "emerald" },
    { href: "/cart", title: pick("Coșul meu", "My cart"), description: pick("Produse grupate pentru următoarea cumpărătură.", "Products grouped for your next shopping trip."), icon: ShoppingCart, tone: "amber" },
    { href: "/missions", title: pick("Misiuni", "Missions"), description: pick("Câștigă CeCoins și ajută catalogul României să crească.", "Earn CeCoins and help the Romania catalog grow."), icon: Gift, tone: "amber" },
    { href: "/preferences", title: pick("Preferințe", "Preferences"), description: pick("Setează cum alegi alternativele.", "Set how alternatives should be chosen."), icon: SlidersHorizontal, tone: "violet" },
    { href: "/live-assistant", title: pick("AI vizual în curând", "AI visual coming soon"), description: pick("Scanarea prin cod de bare este activă. Identificarea după ambalaj va fi disponibilă pentru Pro și Family.", "Barcode scanning is active. Package recognition will be available for Pro and Family."), icon: ScanLine, tone: "violet" },
    { href: "/history", title: pick("Istoric", "History"), description: pick("Revino la scanările și analizele recente.", "Return to your recent scans and analyses."), icon: Clock3, tone: "cyan" },
    { href: "/favorites", title: pick("Favorite", "Favorites"), description: pick("Păstrează alternativele care merită repetate.", "Keep the alternatives worth buying again."), icon: Heart, tone: "amber" },
    { href: "/submit-product", title: pick("Contribuie produs", "Contribute product"), description: pick("Completează catalogul când un produs lipsește.", "Complete the catalog when a product is missing."), icon: ListPlus, tone: "cyan" },
  ];

  const findAction = (href) => actions.find((action) => action.href === href);
  const mobilePrimaryActions = ["/barcode-scan", "/store"].map(findAction).filter(Boolean);
  const mobileSecondaryActions = [
    "/cart",
    "/submit-product",
    "/history",
    "/catalog-romania",
    "/preferences",
  ].map(findAction).filter(Boolean);

  const loadDashboardData = useCallback(async (userId, profile = null) => {
    try {
      if (!userId) return;
      setLoadError("");
      const profileQuery = profile?.id ? `?profile_id=${encodeURIComponent(profile.id)}` : "";
      const response = await fetch(`${API_URL}/dashboard/summary${profileQuery}`, {
        cache: "no-store",
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || pick("Datele nu au putut fi încărcate. Reîncearcă în câteva clipe.", "Your data could not be loaded. Try again in a few moments."));
      }

      setCounts({
        cart: data.counts?.cart || 0,
        history: data.counts?.history || 0,
        favorites: data.counts?.favorites || 0,
      });
      setLastScannedProduct(data.lastScannedProduct || "-");
      if (data.billing) setBilling(data.billing);
    } catch (error) {
      setLoadError(error.message);
    } finally {
      setIsLoading(false);
    }
  }, [pick]);

  const loadGamificationData = useCallback(async () => {
    setIsGamificationLoading(true);
    setGamificationError("");

    try {
      const response = await fetch(`${API_URL}/gamification/summary`, { cache: "no-store" });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || pick("Misiunile nu s-au putut încărca.", "Missions could not be loaded."));
      }

      setGamification(data);
    } catch {
      setGamification(null);
      setGamificationError(
        pick(
          "Misiunile nu s-au putut încărca. Reîncearcă în câteva secunde.",
          "Missions could not be loaded. Try again in a few seconds."
        )
      );
    } finally {
      setIsGamificationLoading(false);
    }
  }, [pick]);

  const syncCecoinCheckout = useCallback(async (sessionId) => {
    if (!sessionId) return false;

    setShopMessage(pick("Se confirmă pachetul CeCoins...", "Confirming your CeCoins pack..."));

    const response = await fetch(`${API_URL}/gamification/coin-checkout/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId }),
    });
    const data = await readApiJson(response);

    if (!response.ok) {
      throw new Error(data.error || pick("CeCoins nu au putut fi actualizate.", "CeCoins could not be updated."));
    }

    setGamification(data.summary);
    setShopMessage(data.message || pick("CeCoins au fost actualizate.", "CeCoins have been updated."));
    return true;
  }, [pick]);

  useEffect(() => {
    let isMounted = true;
    let currentUserId = null;
    let gamificationIdleHandle = null;
    let gamificationTimeoutHandle = null;

    function cancelScheduledGamificationLoad() {
      if (gamificationIdleHandle !== null && "cancelIdleCallback" in window) {
        window.cancelIdleCallback(gamificationIdleHandle);
      }
      if (gamificationTimeoutHandle !== null) {
        window.clearTimeout(gamificationTimeoutHandle);
      }

      gamificationIdleHandle = null;
      gamificationTimeoutHandle = null;
    }

    function scheduleGamificationLoad() {
      if (!isMounted) return;
      cancelScheduledGamificationLoad();

      const run = () => {
        gamificationIdleHandle = null;
        gamificationTimeoutHandle = null;
        if (isMounted) loadGamificationData();
      };

      if ("requestIdleCallback" in window) {
        gamificationIdleHandle = window.requestIdleCallback(run, { timeout: 1800 });
      } else {
        gamificationTimeoutHandle = window.setTimeout(run, 350);
      }
    }

    function handleProfileChange(event) {
      if (!isMounted || !currentUserId) return;
      loadDashboardData(currentUserId, event.detail || getActiveProfile());
      scheduleGamificationLoad();
    }

    window.addEventListener("cealeg:profile-change", handleProfileChange);

    queueMicrotask(async () => {
      const response = await fetch(`${API_URL}/auth/me`);
      if (!response.ok) {
        localStorage.removeItem("cealeg_user");
        window.location.assign("/login");
        return;
      }
      const data = await response.json();
      localStorage.setItem("cealeg_user", JSON.stringify(data.user));
      currentUserId = data.user.id;
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
                  "Contul este creat, dar emailul de bun venit nu a putut fi trimis acum.",
                  "The account is ready, but the welcome email could not be sent right now."
                )
              : pick(
                  "Contul este creat. Emailurile nu sunt conectate încă pe server.",
                  "The account is ready. Email delivery is not connected on the server yet."
                )
          );
        }
      }

      const dashboardPromise = loadDashboardData(data.user.id, getActiveProfile());
      const queryParams = new URLSearchParams(window.location.search);
      const cecoinStatus = queryParams.get("cecoins");
      const cecoinSessionId = queryParams.get("session_id");

      if (cecoinStatus === "success") {
        await dashboardPromise;

        if (cecoinSessionId) {
          try {
            await syncCecoinCheckout(cecoinSessionId);
          } catch (error) {
            setShopMessage(
              error.message || pick(
                "Plata a fost confirmată, dar CeCoins nu au putut fi actualizate automat.",
                "Payment was confirmed, but CeCoins could not be updated automatically."
              )
            );
            scheduleGamificationLoad();
          }
        } else {
          setShopMessage(
            pick(
              "Plata a fost confirmată. Dacă CeCoins nu apar imediat, webhook-ul Stripe le va sincroniza în scurt timp.",
              "Payment was confirmed. If CeCoins do not appear immediately, Stripe webhook will sync them shortly."
            )
          );
        }

        window.history.replaceState(null, "", "/dashboard");
      } else if (cecoinStatus === "cancelled") {
        setShopMessage(pick("Cumpărarea de CeCoins a fost anulată.", "CeCoins purchase was cancelled."));
        window.history.replaceState(null, "", "/dashboard");
      }

      if (!(cecoinStatus === "success" && cecoinSessionId)) {
        dashboardPromise.finally(scheduleGamificationLoad);
      }
    });

    return () => {
      isMounted = false;
      cancelScheduledGamificationLoad();
      window.removeEventListener("cealeg:profile-change", handleProfileChange);
    };
  }, [loadDashboardData, loadGamificationData, pick, syncCecoinCheckout]);

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
              `Am trimis confirmarea la ${data.email}. Contul nu se șterge până nu confirmi din email.`,
              `We sent the confirmation to ${data.email}. The account is not deleted until you confirm by email.`
            )
          : data.message || pick("Verifică emailul pentru confirmare.", "Check your email to confirm.")
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

  async function copyInviteCode() {
    if (!user?.inviteCode) return;

    try {
      await navigator.clipboard.writeText(user.inviteCode);
      setInviteCopyNotice(pick("Cod copiat.", "Code copied."));
    } catch {
      setInviteCopyNotice(pick("Copiază manual codul afișat.", "Copy the displayed code manually."));
    }

    setTimeout(() => setInviteCopyNotice(""), 2200);
  }

  async function buyCoinPack(packId) {
    if (!packId || buyingPackId) return;
    if (!user?.id) {
      setShopMessage(
        pick(
          "Ai nevoie de cont ca sa cumperi CeCoins. Intra in cont ori creeaza unul, apoi revino la plata.",
          "You need an account to buy CeCoins. Sign in or create an account, then return to checkout."
        )
      );
      return;
    }

    setBuyingPackId(packId);
    setShopMessage("");
    trackEvent("checkout_started", {
      checkoutType: "cecoins",
      packId,
      source: "dashboard",
    });
    trackEvent("cecoins_checkout", {
      packId,
      source: "dashboard",
    });

    try {
      const response = await fetch(`${API_URL}/gamification/coin-checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ packId }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          setShopMessage(
            pick(
              "Sesiunea a expirat. Intra din nou in cont ca sa cumperi CeCoins.",
              "Your session expired. Sign in again to buy CeCoins."
            )
          );
          return;
        }

        throw new Error(
          getApiErrorMessage(
            data,
            pick,
            "Pachetul CeCoins nu poate fi cumparat acum.",
            "This CeCoins pack cannot be purchased right now."
          )
        );
      }

      window.location.assign(data.checkoutUrl);
    } catch (error) {
      setShopMessage(error.message);
      setBuyingPackId("");
    }
  }

  function formatBonusDate(value) {
    if (!value) return "";

    return new Intl.DateTimeFormat("ro-RO", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300">{pick("Se încarcă panoul...", "Loading dashboard...")}</p>
      </main>
    );
  }

  const inviteCode = user.inviteCode || "";
  const displayedInviteCode = isInviteVisible && inviteCode
    ? inviteCode
    : inviteCode
      ? "•".repeat(inviteCode.length)
      : pick("Se generează...", "Generating...");
  const bonusUntil = billing?.usage?.bonusUnlimitedUntil || user.bonusUnlimitedUntil;
  const bonusCredits = billing?.usage?.bonusScanCredits ?? user.bonusScanCredits ?? 0;
  const usage = billing?.usage || {};
  const hasUnlimitedScans = Boolean(usage.isUnlimited);
  const monthlyLimit = usage.monthlyScanLimit ?? usage.weeklyScanLimit;
  const monthlyRemaining = usage.monthlyScansRemaining ?? usage.weeklyScansRemaining;
  const freeScanValue = hasUnlimitedScans
    ? pick("Nelimitat", "Unlimited")
    : Number.isFinite(monthlyLimit)
      ? `${monthlyRemaining ?? 0}/${monthlyLimit}`
      : "-";
  const freeScanDetail = hasUnlimitedScans
    ? pick("scanări prin plan", "plan scans")
    : pick("rămase luna aceasta", "left this month");
  const missions = gamification?.missions || [];
  const completedRewards = gamification?.completedMissions ?? 0;
  const claimedRewards = gamification?.claimedMissions ?? 0;
  const rewardLevel = gamification?.level || (
    completedRewards >= 4
      ? pick("Avansat", "Advanced")
      : completedRewards >= 2
        ? pick("În creștere", "Building")
        : pick("Start bun", "Good start")
  );
  const totalMissionCount = gamification?.totalMissions || 5;
  const rewardProgress = Math.round((completedRewards / Math.max(totalMissionCount, 1)) * 100);
  const coinBalance = gamification?.coins ?? 0;
  const dailyClaimedCoins = gamification?.dailyClaimedCoins ?? 0;
  const dailyCoinLimit = gamification?.dailyCoinLimit ?? 40;
  const readyMissionCount = missions.filter((mission) => {
    const progress = Math.round(Number(mission.progress || 0));
    const isAutomatic = mission.seriesId === "invite" || mission.automatic;
    const isClaimed = Boolean(mission.claimed || mission.claimedToday);
    return !isAutomatic && !isClaimed && (mission.claimable || progress >= 100);
  }).length;
  const nextMission = missions.find((mission) => {
    const isClaimed = Boolean(mission.claimed || mission.claimedToday);
    return !isClaimed && mission.seriesId !== "invite" && !mission.automatic;
  }) || missions[0];
  const nextMissionProgress = nextMission
    ? Math.min(100, Math.max(0, Math.round(Number(nextMission.progress || 0))))
    : 0;
  const primaryDashboardAction = readyMissionCount > 0
    ? {
        href: "/missions",
        title: pick("Revendica CeCoins", "Claim CeCoins"),
        description: pick(
          `${readyMissionCount} misiuni sunt gata. Intră și revendica recompensa.`,
          `${readyMissionCount} missions are ready. Open them and claim your reward.`
        ),
        icon: Trophy,
        tone: "border-yellow-300/35 bg-yellow-300/10 text-yellow-50",
        button: pick("Deschide misiunile", "Open missions"),
      }
    : {
        href: "/barcode-scan",
        title: pick("Scanează urmatorul produs", "Scan the next product"),
        description: pick(
          "Camera, codul de bare și produsul negăsit sunt pregătite pentru mobil.",
          "Camera, barcode and missing-product flow are ready for mobile."
        ),
        icon: Barcode,
        tone: "border-emerald-300/35 bg-emerald-300/10 text-emerald-50",
        button: pick("Porneste scanarea", "Start scanning"),
      };
  const PrimaryDashboardIcon = primaryDashboardAction.icon;
  const fallbackCoinPacks = [
    {
      id: "bronze",
      title: "Bronze CeCoins",
      coins: 500,
      priceText: "9,99 lei",
      configured: false,
      image: CECOIN_PACK_VISUALS.bronze.image,
      icon: CECOIN_PACK_VISUALS.bronze.icon,
    },
    {
      id: "gold",
      title: "Gold CeCoins",
      coins: 1200,
      priceText: "19,99 lei",
      configured: false,
      image: CECOIN_PACK_VISUALS.gold.image,
      icon: CECOIN_PACK_VISUALS.gold.icon,
    },
    {
      id: "diamond",
      title: "Diamond CeCoins",
      coins: 3000,
      priceText: "39,99 lei",
      configured: false,
      image: CECOIN_PACK_VISUALS.diamond.image,
      icon: CECOIN_PACK_VISUALS.diamond.icon,
    },
  ];
  const coinPacks = gamification?.coinPacks?.length ? gamification.coinPacks : fallbackCoinPacks;
  const walletCards = [
    {
      label: pick("Plan", "Plan"),
      value: String(usage.plan || "free").toUpperCase(),
      detail: hasUnlimitedScans ? pick("scanări nelimitate", "unlimited scans") : pick("5 scanări gratuite lunar", "5 free scans monthly"),
      icon: Trophy,
      tone: "border-violet-300/25 bg-violet-300/[0.08] text-violet-100",
      actionHref: "/pricing",
      actionLabel: pick("Vezi planurile", "See plans"),
    },
    {
      label: pick("Scanări", "Scans"),
      value: freeScanValue,
      detail: freeScanDetail,
      icon: ScanLine,
      tone: "border-cyan-300/25 bg-cyan-300/[0.08] text-cyan-100",
    },
    {
      label: pick("Bonus", "Bonus"),
      value: bonusCredits > 0 ? `+${bonusCredits}` : bonusUntil ? pick("Activ", "Active") : "0",
      detail: bonusUntil ? pick("nelimitat temporar", "temporary unlimited") : pick("scanări bonus", "bonus scans"),
      icon: Gift,
      tone: "border-yellow-300/25 bg-yellow-300/[0.08] text-yellow-100",
    },
    {
      label: "CeCoins",
      value: coinBalance,
      detail: pick(`${dailyClaimedCoins}/${dailyCoinLimit} azi`, `${dailyClaimedCoins}/${dailyCoinLimit} today`),
      icon: Coins,
      image: "/brand/CeCoin.webp",
      tone: "border-emerald-300/25 bg-emerald-300/[0.08] text-emerald-100",
      actionHref: "#cumpara-cecoins",
      actionLabel: pick("Cumpără CeCoins", "Buy CeCoins"),
    },
  ];
  const coinPackPurchasePanel = coinPacks.length > 0 ? (
    <div id="cumpara-cecoins" className="rounded-2xl border border-yellow-300/20 bg-yellow-300/[0.055] p-5 scroll-mt-24">
      <div className="flex items-center justify-between gap-3">
        <p className="inline-flex items-center gap-2 text-sm font-black text-yellow-100">
          <Image src="/brand/CeCoin.webp" alt="" width={28} height={28} className="rounded-full object-cover" />
          {pick("Cumpără CeCoins", "Buy CeCoins")}
        </p>
        <span className="rounded-full border border-yellow-300/25 px-3 py-1 text-xs font-black text-yellow-100">
          {coinBalance} CC
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-gray-400">
        {pick(
          "Completează rapid soldul când vrei să activezi recompense fără să aștepți misiunile.",
          "Top up your balance when you want to unlock rewards without waiting for missions."
        )}
      </p>
      <div className="mt-4 space-y-2">
        {coinPacks.map((pack) => {
          const packVisual = CECOIN_PACK_VISUALS[pack.id] || {};
          const packImage = normalizeCecoinAsset(pack.image || packVisual.image);

          return (
            <button
              key={pack.id}
              type="button"
              onClick={() => buyCoinPack(pack.id)}
              disabled={!pack.configured || buyingPackId === pack.id}
              className="flex w-full items-center justify-between gap-3 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-left transition hover:border-yellow-300/35 disabled:cursor-not-allowed disabled:opacity-55"
            >
              <span className="flex min-w-0 items-center gap-3">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-white/5">
                  <Image
                    src={packImage}
                    alt=""
                    width={96}
                    height={96}
                    className="h-full w-full object-cover"
                    sizes="48px"
                  />
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-black text-white">{pack.title}</span>
                  <span className="block text-xs text-gray-400">{pack.coins} CeCoins</span>
                </span>
              </span>
              <span className="shrink-0 text-sm font-black text-yellow-100">
                {buyingPackId === pack.id
                  ? pick("Se deschide...", "Opening...")
                  : pack.configured
                    ? pack.priceText
                    : pick("În curând", "Soon")}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  ) : null;

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader />
      <section className="ce-shell ce-page pb-24 md:pb-12">
        <div className="mb-8 flex items-center justify-between gap-4">
          <Link href="/" className="inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white">
            <ArrowLeft size={16} /> {pick("Pagina principală", "Home")}
          </Link>
          <button onClick={logout} className="inline-flex items-center gap-2 rounded-lg border border-red-400/30 px-4 py-2.5 text-sm font-semibold text-red-300 hover:bg-red-400/10">
            <LogOut size={16} /> {pick("Deconectare", "Sign out")}
          </button>
        </div>

        <div className="ce-panel ce-lifted-shell ce-reveal p-6 md:p-8">
          <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
            <div className="max-w-2xl">
              <p className="text-sm font-bold text-cyan-200">{pick("Spațiul tău", "Your space")}</p>
              <h1 className="mt-3 text-4xl font-bold md:text-5xl">{pick("Salut", "Hello")}, {user.name}</h1>
              <p className="mt-4 text-gray-300">
                {pick("Continuă cumpărăturile sau scanează un produs nou pentru recomandări potrivite preferințelor tale.", "Continue shopping or scan a new product for recommendations matched to your preferences.")}
              </p>
            </div>

            <div className="grid w-full grid-cols-2 gap-2 xl:w-[480px]">
              {walletCards.map(({ label, value, detail, icon: Icon, image, tone, actionHref, actionLabel }) => (
                <div key={label} className={`relative rounded-lg border p-3 pr-9 ${tone}`}>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-black uppercase tracking-wide opacity-80">{label}</p>
                    {image ? (
                      <Image src={image} alt="" width={20} height={20} className="rounded-full object-cover" />
                    ) : (
                      <Icon size={15} />
                    )}
                  </div>
                  <p className="mt-1 truncate text-xl font-black">{value}</p>
                  <p className="mt-1 text-xs font-bold opacity-75">{detail}</p>
                  {actionHref && (
                    <Link
                      href={actionHref}
                      className="absolute bottom-2 right-2 inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/15 bg-white/10 text-white transition hover:bg-white hover:text-black"
                      aria-label={actionLabel}
                      title={actionLabel}
                    >
                      <Plus size={14} strokeWidth={3} />
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </div>

          <InlineNotice message={loadError} tone="warning" className="mt-6" />

          <InlineNotice message={emailStatusNotice} tone="info" className="mt-6" />

          {isLoading && !loadError && (
            <div className="mt-6 rounded-lg border border-white/10 bg-white/[0.035] px-4 py-3 text-sm font-bold text-gray-300">
              {pick("Actualizez datele contului...", "Refreshing account data...")}
            </div>
          )}

          {billing?.usage && (
            <div className="ce-usage-banner mt-6 flex flex-col gap-3 rounded-lg border p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-bold uppercase tracking-wide text-cyan-200">{billing.usage.plan}</p>
                <p className="mt-1 text-sm">
                  {billing.usage.isUnlimited
                    ? pick("Ai scanări nelimitate active.", "Unlimited scans are active.")
                    : pick(
                        `Mai ai ${billing.usage.monthlyScansRemaining ?? billing.usage.weeklyScansRemaining}/${billing.usage.monthlyScanLimit ?? billing.usage.weeklyScanLimit} scanări gratuite luna aceasta.`,
                        `${billing.usage.monthlyScansRemaining ?? billing.usage.weeklyScansRemaining}/${billing.usage.monthlyScanLimit ?? billing.usage.weeklyScanLimit} free scans left this month.`
                      )}
                </p>
              </div>
              <Link href="/pricing" className="inline-flex justify-center rounded-lg bg-white px-4 py-2.5 text-sm font-black text-black hover:bg-cyan-100">
                {pick("Vezi planurile", "View plans")}
              </Link>
            </div>
          )}

          <Link
            href={primaryDashboardAction.href}
            className={`mt-6 flex flex-col gap-4 rounded-2xl border p-5 transition hover:-translate-y-0.5 sm:flex-row sm:items-center sm:justify-between ${primaryDashboardAction.tone}`}
          >
            <span className="flex items-start gap-3">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white text-black">
                <PrimaryDashboardIcon size={22} />
              </span>
              <span>
                <span className="block text-xl font-black">{primaryDashboardAction.title}</span>
                <span className="mt-1 block text-sm leading-6 text-gray-200">
                  {primaryDashboardAction.description}
                </span>
              </span>
            </span>
            <span className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-black text-black">
              {primaryDashboardAction.button}
              <ArrowRight size={17} />
            </span>
          </Link>

          <div className="mt-6 space-y-3 md:hidden">
            <div className="rounded-2xl border border-emerald-300/25 bg-emerald-300/[0.08] p-4">
              <p className="text-xs font-black uppercase tracking-wide text-emerald-100">
                {pick("La raft", "At the shelf")}
              </p>
              <h2 className="mt-2 text-2xl font-black">
                {pick("Alege rapid produsul potrivit.", "Choose the right product faster.")}
              </h2>
              <p className="mt-2 text-sm leading-6 text-gray-300">
                {pick(
                  "Pe telefon, începe cu scanarea codului sau caută produsul după nume. Restul rămâne la un tap distanță.",
                  "On mobile, start with barcode scanning or product search. Everything else stays one tap away."
                )}
              </p>
              <div className="mt-4 grid gap-3">
                {mobilePrimaryActions.map(({ href, title, description, icon: Icon, tone }) => {
                  const selectedTone = ACTION_TONES[tone] || ACTION_TONES.cyan;

                  return (
                    <Link
                      key={href}
                      href={href}
                      className={`flex items-center gap-3 rounded-xl border p-4 ${selectedTone.card}`}
                    >
                      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${selectedTone.icon}`}>
                        <Icon size={21} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-base font-black">{title}</span>
                        <span className={`mt-0.5 block text-xs leading-5 ${selectedTone.description}`}>{description}</span>
                      </span>
                      <ArrowRight size={17} className="shrink-0" />
                    </Link>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {mobileSecondaryActions.map(({ href, title, icon: Icon, tone }) => {
                const selectedTone = ACTION_TONES[tone] || ACTION_TONES.cyan;

                return (
                  <Link
                    key={href}
                    href={href}
                    className={`flex min-h-24 flex-col justify-between rounded-xl border p-3 ${selectedTone.card}`}
                  >
                    <Icon size={20} />
                    <span className="mt-3 text-sm font-black leading-5">{title}</span>
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.06] p-5">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <p className="inline-flex items-center gap-2 text-sm font-black text-cyan-200">
                  <Gift size={17} />
                  {pick("Invită prieteni", "Invite friends")}
                </p>
                <h2 className="mt-2 text-2xl font-black">
                  {pick("Primești scanări nelimitate pentru invitații confirmate.", "Get unlimited scans for confirmed invites.")}
                </h2>
                <p className="mt-2 text-sm leading-6 text-gray-300">
                  {pick(
                    "Când cineva își creează cont cu codul tău și confirmă emailul, amândoi primiți 2 zile de scanări nelimitate.",
                    "When someone creates an account with your code and confirms their email, both of you get 2 days of unlimited scans."
                  )}
                </p>
                <p className="mt-3 text-sm text-gray-400">
                  {bonusUntil
                    ? pick(`Bonus activ până la ${formatBonusDate(bonusUntil)}.`, `Bonus active until ${formatBonusDate(bonusUntil)}.`)
                    : pick("Nu ai bonus temporar activ acum.", "No temporary bonus is active right now.")}
                </p>
              </div>

              <div className="w-full rounded-xl border border-white/10 bg-black/25 p-4 lg:w-[360px]">
                <p className="text-xs font-black uppercase tracking-wide text-gray-400">
                  {pick("Codul tău", "Your code")}
                </p>
                <div className="mt-3 flex items-center gap-2 rounded-lg border border-white/10 bg-black/35 p-2">
                  <code className="min-w-0 flex-1 truncate px-2 font-mono text-lg font-black tracking-[0.18em] text-white">
                    {displayedInviteCode}
                  </code>
                  <button
                    type="button"
                    onClick={() => setIsInviteVisible((value) => !value)}
                    className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/10 text-gray-200 hover:bg-white/10"
                    aria-label={pick("Afișează codul", "Reveal code")}
                  >
                    {isInviteVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                  <button
                    type="button"
                    onClick={copyInviteCode}
                    disabled={!inviteCode}
                    className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white text-black hover:bg-cyan-100 disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label={pick("Copiază codul", "Copy code")}
                  >
                    <Copy size={18} />
                  </button>
                </div>
                {inviteCopyNotice && (
                  <p className="mt-2 text-sm font-bold text-cyan-200">{inviteCopyNotice}</p>
                )}
              </div>
            </div>
          </div>

          <div className="mt-6">
            <FamilyProfiles />
          </div>

          <div className="mt-6 rounded-2xl border border-violet-300/20 bg-violet-300/[0.065] p-4 md:hidden">
            <p className="inline-flex items-center gap-2 text-sm font-black text-violet-100">
              <Trophy size={17} />
              {pick("Misiuni", "Missions")}
            </p>
            <div className="mt-3 flex items-end justify-between gap-3">
              <div>
                <p className="text-2xl font-black">{coinBalance} CeCoins</p>
                <p className="mt-1 text-xs font-bold text-gray-400">
                  {readyMissionCount
                    ? pick(`${readyMissionCount} gata de revendicat`, `${readyMissionCount} ready to claim`)
                    : pick("Progresul se strânge din scanări și contribuții.", "Progress builds from scans and contributions.")}
                </p>
              </div>
              <span className="rounded-full border border-white/10 bg-black/25 px-3 py-1 text-xs font-black text-cyan-100">
                {rewardLevel}
              </span>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-violet-200 transition-all" style={{ width: `${rewardProgress}%` }} />
            </div>
            <Link
              href="/missions"
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-black text-black hover:bg-cyan-100"
            >
              <Trophy size={17} />
              {pick("Deschide misiunile", "Open missions")}
            </Link>
          </div>

          <div className="mt-6 hidden rounded-2xl border border-violet-300/20 bg-violet-300/[0.055] p-5 md:block">
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
              <div>
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="inline-flex items-center gap-2 text-sm font-black text-violet-200">
                      <Trophy size={17} />
                      {pick("Misiuni și recompense", "Missions and rewards")}
                    </p>
                    <h2 className="mt-2 text-2xl font-black">
                      {rewardLevel} · {coinBalance} CeCoins
                    </h2>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-300">
                      {pick(
                        "Vezi rapid soldul și progresul. Pentru revendicare, clasament și detalii intră în pagina Misiuni.",
                        "See your balance and progress at a glance. Claiming, leaderboard and details live on the Missions page."
                      )}
                    </p>
                  </div>
                  <div className="w-full rounded-xl border border-white/10 bg-black/25 p-4 lg:w-[320px]">
                    <div className="flex items-center justify-between text-sm font-black">
                      <span className="inline-flex items-center gap-2 text-cyan-200">
                        <Sparkles size={16} />
                        {pick("Progres general", "Overall progress")}
                      </span>
                      <span>{completedRewards}/{totalMissionCount}</span>
                    </div>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                      <div className="h-full rounded-full bg-cyan-300 transition-all" style={{ width: `${rewardProgress}%` }} />
                    </div>
                    <p className="mt-3 text-xs font-bold text-gray-400">
                      {pick("Revendicate", "Claimed")}: {claimedRewards}/{totalMissionCount}
                    </p>
                  </div>
                </div>

                {isGamificationLoading && !gamification && (
                  <p className="mt-4 rounded-lg border border-white/10 bg-black/20 px-4 py-3 text-sm font-bold text-gray-300">
                    {pick("Se încarcă misiunile și recompensele...", "Loading missions and rewards...")}
                  </p>
                )}

                {gamificationError && !isGamificationLoading && (
                  <div className="mt-4 flex flex-col gap-3 rounded-lg border border-yellow-300/25 bg-yellow-300/10 px-4 py-3 text-sm text-yellow-50 sm:flex-row sm:items-center sm:justify-between">
                    <p className="font-bold">{gamificationError}</p>
                    <button
                      type="button"
                      onClick={loadGamificationData}
                      className="rounded-lg bg-white px-4 py-2 font-black text-black hover:bg-yellow-100"
                    >
                      {pick("Reîncearcă", "Retry")}
                    </button>
                  </div>
                )}

                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <p className="text-xs font-black uppercase tracking-wide text-gray-400">
                      {pick("Gata", "Ready")}
                    </p>
                    <p className="mt-2 text-3xl font-black text-cyan-100">{readyMissionCount}</p>
                    <p className="mt-1 text-xs leading-5 text-gray-400">
                      {pick("misiuni de revendicat în pagina dedicată", "missions to claim on the dedicated page")}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <p className="text-xs font-black uppercase tracking-wide text-gray-400">
                      {pick("Revendicate", "Claimed")}
                    </p>
                    <p className="mt-2 text-3xl font-black text-violet-100">{claimedRewards}</p>
                    <p className="mt-1 text-xs leading-5 text-gray-400">
                      {pick("din misiunile active", "from active missions")}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                    <p className="text-xs font-black uppercase tracking-wide text-gray-400">
                      {pick("Următoarea", "Next")}
                    </p>
                    <p className="mt-2 truncate text-sm font-black text-white">
                      {nextMission?.title || nextMission?.label || pick("Nicio misiune încă", "No mission yet")}
                    </p>
                    <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                      <div className="h-full rounded-full bg-violet-200 transition-all" style={{ width: `${nextMissionProgress}%` }} />
                    </div>
                  </div>
                </div>

                <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                  <Link
                    href="/missions"
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-black text-black hover:bg-cyan-100"
                  >
                    <Trophy size={18} />
                    {pick("Deschide misiunile", "Open missions")}
                  </Link>
                  <Link
                    href="/submit-product"
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-yellow-300/30 px-5 py-3 text-sm font-black text-yellow-100 hover:bg-yellow-300/10"
                  >
                    <ListPlus size={18} />
                    {pick("Adaugă produs lipsă", "Add missing product")}
                  </Link>
                </div>
              </div>

              <div className="space-y-4">
                {coinPackPurchasePanel}
              </div>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
            {[
              [pick("Produse în coș", "Cart products"), counts.cart, "ce-stat-cyan", "text-cyan-200"],
              [pick("Scanări salvate", "Saved scans"), counts.history, "ce-stat-cyan", "text-cyan-200"],
              [pick("Favorite", "Favorites"), counts.favorites, "ce-stat-violet", "text-violet-200"],
              [pick("Ultima scanare", "Latest scan"), lastScannedProduct, "ce-stat-amber", "text-yellow-200"],
            ].map(([label, value, tone, valueClass]) => (
              <InteractiveSurface key={label} className={`ce-stat-card ${tone} p-5`}>
                <p className="relative z-10 text-sm font-semibold text-gray-400">{label}</p>
                <p className={`relative z-10 mt-2 truncate text-2xl font-black ${valueClass}`}>{value}</p>
              </InteractiveSurface>
            ))}
          </div>

          <div className="mt-9 hidden flex-col gap-2 md:flex md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-black text-cyan-200">
                {pick("Acțiuni rapide", "Quick actions")}
              </p>
              <h2 className="mt-1 text-2xl font-black">
                {pick("Ce vrei să faci acum?", "What do you want to do now?")}
              </h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-gray-400">
              {pick(
                "Scanează la raft, caută un produs sau continuă lista de cumpărături.",
                "Scan at the shelf, search for a product or continue your shopping list."
              )}
            </p>
          </div>

          <div className="mt-8 hidden gap-4 md:grid md:grid-cols-2 2xl:grid-cols-4">
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
            <Link href="/admin" className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-cyan-200 hover:text-white">
              <ShieldCheck size={16} /> {pick("Deschide administrarea", "Open administration")}
            </Link>
          )}

          <div className="ce-danger-panel mt-8 rounded-2xl border p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <p className="flex items-center gap-2 text-sm font-black text-red-300">
                  <Trash2 size={16} /> {pick("Ștergere cont", "Delete account")}
                </p>
                <h2 className="mt-2 text-2xl font-black">{pick("Vrei să închizi contul?", "Want to close your account?")}</h2>
                <p className="mt-2 leading-7 text-gray-300">
                  {pick(
                    "Îți trimitem un email de confirmare. Contul, istoricul, coșul, favoritele și contribuțiile tale se șterg doar după confirmarea din email.",
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
                  {pick("Șterge contul", "Delete account")}
                </button>
              ) : (
                <div className="shrink-0 space-y-3 rounded-xl border border-red-400/25 bg-black/25 p-4">
                  <p className="max-w-xs text-sm leading-6 text-red-100">
                    {pick(
                      "Confirmarea vine pe email. După apăsare, verifică inboxul.",
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
                      {pick("Anulează", "Cancel")}
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

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-white/10 bg-[#0b0f14]/95 px-3 py-2 shadow-2xl backdrop-blur md:hidden">
        <div className="mx-auto grid max-w-xl grid-cols-3 gap-2">
          <Link
            href="/barcode-scan"
            className="flex min-h-14 flex-col items-center justify-center rounded-xl bg-emerald-400 px-2 py-2 text-xs font-black text-black"
          >
            <Barcode size={19} />
            <span className="mt-1">Scanează</span>
          </Link>
          <Link
            href="/store"
            className="flex min-h-14 flex-col items-center justify-center rounded-xl border border-cyan-300/25 px-2 py-2 text-xs font-black text-cyan-100"
          >
            <ScanLine size={19} />
            <span className="mt-1">Caută</span>
          </Link>
          <Link
            href="/missions"
            className="relative flex min-h-14 flex-col items-center justify-center rounded-xl border border-yellow-300/25 px-2 py-2 text-xs font-black text-yellow-100"
          >
            {readyMissionCount > 0 && (
              <span className="absolute right-2 top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-yellow-300 px-1 text-[10px] text-black">
                {readyMissionCount}
              </span>
            )}
            <Trophy size={19} />
            <span className="mt-1">Misiuni</span>
          </Link>
        </div>
      </nav>
    </main>
  );
}

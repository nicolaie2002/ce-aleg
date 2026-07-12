"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Award,
  Barcode,
  CheckCircle2,
  Clock3,
  Coins,
  Gift,
  Heart,
  ListPlus,
  PackagePlus,
  RefreshCw,
  ScanLine,
  ShoppingCart,
  Sparkles,
  Trophy,
  Users,
} from "lucide-react";
import { API_URL } from "../config";
import { AppHeader } from "../components/AppHeader";
import { InlineNotice } from "../components/InlineNotice";
import { InteractiveSurface } from "../components/InteractiveSurface";
import { useLocale } from "../components/LocaleProvider";
import { readApiJson } from "../utils/apiResponse";

const MISSION_ICONS = {
  scan: ScanLine,
  cart: ShoppingCart,
  favorite: Heart,
  catalog: ListPlus,
  streak: Clock3,
  invite: Gift,
};

function clampProgress(value) {
  return Math.min(100, Math.max(0, Math.round(Number(value || 0))));
}

function getMissionHref(mission) {
  const seriesId = mission?.seriesId || mission?.icon;

  if (seriesId === "scan") return "/barcode-scan";
  if (seriesId === "cart") return "/store";
  if (seriesId === "favorite") return "/favorites";
  if (seriesId === "catalog") return "/submit-product";
  if (seriesId === "streak") return "/barcode-scan";
  if (seriesId === "invite") return "/dashboard";

  return "/dashboard";
}

function formatMissionReset(value) {
  if (!value) return "";

  try {
    return new Intl.DateTimeFormat("ro-RO", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return "";
  }
}

export default function MissionsPage() {
  const { pick } = useLocale();
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [claimingMissionId, setClaimingMissionId] = useState("");

  const loadSummary = useCallback(async () => {
    setError("");

    try {
      const response = await fetch(`${API_URL}/gamification/summary?leaderboard=1`, {
        cache: "no-store",
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || pick("Misiunile nu s-au putut încărca.", "Missions could not be loaded."));
      }

      setSummary(data);
    } catch (loadError) {
      setSummary(null);
      setError(
        loadError.message ||
          pick("Misiunile nu s-au putut încărca. Reîncearcă în câteva secunde.", "Missions could not be loaded. Try again in a few seconds.")
      );
    } finally {
      setIsLoading(false);
    }
  }, [pick]);

  useEffect(() => {
    let isMounted = true;

    queueMicrotask(async () => {
      try {
        const authResponse = await fetch(`${API_URL}/auth/me`, { cache: "no-store" });

        if (!authResponse.ok) {
          window.location.assign("/login?next=/missions");
          return;
        }

        const authData = await authResponse.json();
        if (!isMounted) return;

        window.localStorage.setItem("cealeg_user", JSON.stringify(authData.user));
        await loadSummary();
      } catch {
        if (isMounted) {
          setError(pick("Nu am putut verifica sesiunea. Intră din nou în cont.", "Could not verify your session. Sign in again."));
          setIsLoading(false);
        }
      }
    });

    return () => {
      isMounted = false;
    };
  }, [loadSummary, pick]);

  async function claimMission(missionId) {
    if (!missionId || claimingMissionId) return;

    setClaimingMissionId(missionId);
    setMessage("");
    setError("");

    try {
      const response = await fetch(`${API_URL}/gamification/claim`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ missionId }),
      });
      const data = await readApiJson(response);

      if (!response.ok) {
        throw new Error(data.error || pick("Recompensa nu a putut fi revendicată.", "The reward could not be claimed."));
      }

      setSummary(data.summary);
      setMessage(data.message || pick("Recompensă revendicată.", "Reward claimed."));
    } catch (claimError) {
      setError(claimError.message || pick("Recompensa nu a putut fi revendicată.", "The reward could not be claimed."));
    } finally {
      setClaimingMissionId("");
    }
  }

  const missions = useMemo(() => summary?.missions || [], [summary]);
  const completedMissions = summary?.completedMissions || 0;
  const claimedMissions = summary?.claimedMissions || 0;
  const totalMissions = summary?.totalMissions || missions.length || 1;
  const coinBalance = summary?.coins || 0;
  const streakDays = summary?.metrics?.scanStreakDays || 0;
  const progress = clampProgress((completedMissions / Math.max(totalMissions, 1)) * 100);
  const resetAt = formatMissionReset(summary?.missionsResetAt);
  const weeklyLeaderboard = summary?.leaderboard?.weekly?.top || [];
  const currentUserRank = summary?.leaderboard?.weekly?.currentUser?.rank;
  const readyMissions = missions.filter((mission) => {
    const missionProgress = clampProgress(mission.progress);
    return !mission.automatic && !mission.claimed && !mission.claimedToday && (mission.claimable || missionProgress >= 100);
  });
  const catalogMission = useMemo(
    () => missions.find((mission) => mission.seriesId === "catalog") || null,
    [missions]
  );

  if (isLoading && !summary) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#0b0f14] text-white">
        <p className="text-gray-300">{pick("Se încarcă misiunile...", "Loading missions...")}</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#0b0f14] text-white">
      <AppHeader actionHref="/submit-product" actionLabel={pick("Adaugă produs", "Add product")} />

      <section className="ce-shell ce-page">
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)] lg:items-stretch">
          <InteractiveSurface className="ce-lifted-shell overflow-hidden rounded-2xl border border-cyan-300/20 bg-[linear-gradient(145deg,rgba(103,232,249,.13),rgba(250,204,21,.08),rgba(255,255,255,.035))] p-5 md:p-7">
            <p className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1 text-xs font-black text-cyan-100">
              <Sparkles size={15} />
              {pick("Catalogul crește cu fiecare raft", "The catalog grows with every shelf")}
            </p>
            <h1 className="mt-4 text-4xl font-black leading-tight md:text-6xl">
              {pick("Misiuni care îți aduc CeCoins.", "Missions that earn CeCoins.")}
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-gray-300 md:text-lg">
              {pick(
                "Scanezi, salvezi produse și contribui când ceva lipsește. Așa construim un catalog mai bun pentru România fără să așteptăm listele retailerilor.",
                "Scan, save products and contribute when something is missing. This is how we build a better Romania catalog without waiting for retailer feeds."
              )}
            </p>

            <div className="mt-6 grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
              <Link
                href="/barcode-scan"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 text-sm font-black text-black hover:bg-cyan-100"
              >
                <Barcode size={18} />
                {pick("Scanează", "Scan")}
              </Link>
              <Link
                href="/submit-product"
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-yellow-300/35 bg-yellow-300/10 px-4 py-3 text-sm font-black text-yellow-100 hover:bg-yellow-300/20"
              >
                <PackagePlus size={18} />
                {pick("Adaugă lipsă", "Add missing")}
              </Link>
            </div>
          </InteractiveSurface>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-1">
            <div className="rounded-2xl border border-yellow-300/20 bg-yellow-300/[0.06] p-4 md:p-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-black text-yellow-100">CeCoins</p>
                <Image src="/brand/CeCoin.webp" alt="" width={34} height={34} className="rounded-full object-cover" />
              </div>
              <p className="mt-3 text-3xl font-black text-white md:text-4xl">{coinBalance}</p>
              <p className="mt-1 text-xs font-bold text-gray-400">
                {summary?.level || pick("Start bun", "Good start")}
              </p>
            </div>

            <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.06] p-4 md:p-5">
              <div className="flex items-center justify-between gap-3 text-sm font-black text-cyan-100">
                <span>{pick("Progres", "Progress")}</span>
                <span>{completedMissions}/{totalMissions}</span>
              </div>
              <div className="mt-4 h-3 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full bg-cyan-200" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-3 text-xs font-bold text-gray-400">
                {claimedMissions} {pick("revendicate", "claimed")}
                {resetAt ? ` · ${pick("reset la", "resets at")} ${resetAt}` : ""}
              </p>
            </div>

            <div className="col-span-2 rounded-2xl border border-violet-300/20 bg-violet-300/[0.055] p-4 md:p-5 lg:col-span-1">
              <div className="flex items-center justify-between gap-3 text-sm font-black text-violet-100">
                <span>{pick("Streak scanări", "Scan streak")}</span>
                <Clock3 size={18} />
              </div>
              <p className="mt-3 text-3xl font-black text-white md:text-4xl">{streakDays}</p>
              <p className="mt-1 text-xs font-bold text-gray-400">
                {pick("zile la rând active", "active days in a row")}
              </p>
            </div>
          </div>
        </div>

        <InlineNotice message={message} tone="success" className="mt-5" />
        <InlineNotice message={error} tone="warning" className="mt-5" />

        <section className="mt-8 rounded-2xl border border-white/10 bg-white/[0.04] p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="inline-flex items-center gap-2 text-sm font-black text-cyan-200">
                <Award size={17} />
                {pick("Misiunile tale", "Your missions")}
              </p>
              <h2 className="mt-2 text-2xl font-black">
                {readyMissions.length
                  ? pick(`${readyMissions.length} recompense sunt gata`, `${readyMissions.length} rewards are ready`)
                  : pick("Continuă progresul", "Keep building progress")}
              </h2>
            </div>
            <button
              type="button"
              onClick={loadSummary}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-sm font-black text-white hover:bg-white/10"
            >
              <RefreshCw size={16} />
              {pick("Actualizează", "Refresh")}
            </button>
          </div>

          {missions.length ? (
            <div className="ce-mobile-snap-row mt-5 flex gap-4 overflow-x-auto pb-2 md:grid md:grid-cols-2 md:overflow-visible md:pb-0 xl:grid-cols-3">
              {missions.map((mission) => {
                const MissionIcon = MISSION_ICONS[mission.icon] || Award;
                const missionProgress = clampProgress(mission.progress);
                const isAutomatic = mission.seriesId === "invite" || mission.automatic;
                const isClaimed = Boolean(mission.claimed || mission.claimedToday);
                const isClaimable = Boolean(!isAutomatic && !isClaimed && (mission.claimable || missionProgress >= 100));
                const rewardParts = [
                  mission.reward?.coins ? `${mission.reward.coins} CeCoins` : "",
                  mission.reward?.bonusScans ? `+${mission.reward.bonusScans} ${pick("scanări", "scans")}` : "",
                  mission.reward?.bonusDays ? `+${mission.reward.bonusDays} ${pick("zi nelimitată", "unlimited day")}` : "",
                ].filter(Boolean);

                return (
                  <article
                    key={mission.id}
                    className={`min-w-[82vw] snap-start rounded-2xl border p-4 md:min-w-0 ${
                      isClaimable
                        ? "border-cyan-300/35 bg-cyan-300/10"
                        : isClaimed
                          ? "border-violet-300/25 bg-violet-300/[0.06]"
                          : "border-white/10 bg-black/20"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="inline-flex min-w-0 items-center gap-2 text-sm font-black text-white">
                        <MissionIcon size={17} className="shrink-0 text-cyan-200" />
                        <span className="truncate">{mission.title || mission.label}</span>
                      </p>
                      {isClaimable && (
                        <span className="shrink-0 rounded-full bg-cyan-200 px-2 py-1 text-[11px] font-black text-black">
                          {pick("Gata", "Ready")}
                        </span>
                      )}
                      {isClaimed && (
                        <span className="shrink-0 rounded-full bg-violet-200 px-2 py-1 text-[11px] font-black text-black">
                          {mission.claimedToday ? pick("Azi", "Today") : pick("OK", "OK")}
                        </span>
                      )}
                    </div>

                    <p className="mt-3 min-h-10 text-sm leading-6 text-gray-400">
                      {mission.description || mission.detail}
                    </p>

                    <div className="mt-4">
                      <div className="flex items-center justify-between text-xs font-bold text-gray-400">
                        <span>{mission.current}/{mission.target}</span>
                        <span>{missionProgress}%</span>
                      </div>
                      <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
                        <div className="h-full rounded-full bg-cyan-200" style={{ width: `${missionProgress}%` }} />
                      </div>
                    </div>

                    <p className="mt-4 text-xs font-black text-yellow-100">
                      {rewardParts.join(" · ") || pick("Recompensă", "Reward")}
                    </p>

                    <div className="mt-4 grid grid-cols-2 gap-2">
                      <Link
                        href={getMissionHref(mission)}
                        className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs font-black text-white hover:bg-white/10"
                      >
                        {pick("Continuă", "Continue")}
                        <ArrowRight size={14} />
                      </Link>
                      <button
                        type="button"
                        onClick={() => claimMission(mission.id)}
                        disabled={!isClaimable || claimingMissionId === mission.id}
                        className={`rounded-lg px-3 py-2 text-xs font-black ${
                          isClaimable
                            ? "bg-white text-black hover:bg-cyan-100"
                            : "cursor-not-allowed border border-white/10 text-gray-500"
                        }`}
                      >
                        {claimingMissionId === mission.id
                          ? pick("Activez...", "Claiming...")
                          : isAutomatic
                            ? pick("Automat", "Automatic")
                            : isClaimed
                              ? pick("Revendicat", "Claimed")
                              : isClaimable
                                ? pick("Revendică", "Claim")
                                : pick("În progres", "In progress")}
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="mt-5 rounded-xl border border-white/10 bg-black/20 p-5 text-sm text-gray-300">
              {pick("Misiunile apar după prima sincronizare a contului.", "Missions appear after the first account sync.")}
            </p>
          )}
        </section>

        <section className="mt-8 grid gap-4 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <div className="rounded-2xl border border-yellow-300/20 bg-yellow-300/[0.055] p-5">
            <p className="inline-flex items-center gap-2 text-sm font-black text-yellow-100">
              <PackagePlus size={17} />
              {pick("Catalog Builder România", "Romania Catalog Builder")}
            </p>
            <h2 className="mt-2 text-2xl font-black">
              {pick("Produs negăsit? Îl transformi în recompensă.", "Product missing? Turn it into a reward.")}
            </h2>
            <p className="mt-3 text-sm leading-6 text-gray-300">
              {pick(
                "Dacă magazinele nu trimit baze de date, creștem catalogul din scanările reale ale utilizatorilor. Produsele aprobate îmbunătățesc recomandările pentru toată lumea.",
                "If stores do not send feeds, we grow the catalog from real user scans. Approved products improve recommendations for everyone."
              )}
            </p>

            <div className="mt-5 grid gap-3">
              {[
                [Barcode, pick("Scanezi produsul lipsă", "Scan the missing product")],
                [ListPlus, pick("Adaugi poze și eticheta", "Add photos and label data")],
                [Coins, pick("Primești CeCoins după aprobare", "Earn CeCoins after approval")],
              ].map(([Icon, label], index) => (
                <div key={label} className="flex items-center gap-3 rounded-xl border border-white/10 bg-black/20 p-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-black">
                    {index + 1}
                  </span>
                  <Icon size={18} className="text-yellow-100" />
                  <p className="text-sm font-bold text-white">{label}</p>
                </div>
              ))}
            </div>

            <Link
              href="/submit-product"
              className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-yellow-100 sm:w-auto"
            >
              <PackagePlus size={18} />
              {pick("Contribuie produs", "Contribute product")}
            </Link>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <p className="inline-flex items-center gap-2 text-sm font-black text-cyan-200">
                <Trophy size={17} />
                {pick("Clasament săptămânal", "Weekly leaderboard")}
              </p>
              {currentUserRank && (
                <p className="mt-2 text-sm font-bold text-gray-300">
                  {pick("Poziția ta", "Your rank")}: #{currentUserRank}
                </p>
              )}
              <div className="mt-4 space-y-2">
                {weeklyLeaderboard.length ? weeklyLeaderboard.slice(0, 5).map((row) => (
                  <div
                    key={row.userId}
                    className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm ${
                      row.isCurrentUser
                        ? "border-cyan-300/35 bg-cyan-300/10 text-cyan-50"
                        : "border-white/10 bg-black/20 text-gray-300"
                    }`}
                  >
                    <span className="min-w-0 truncate font-bold">#{row.rank} {row.name}</span>
                    <span className="shrink-0 font-black text-yellow-100">{row.coins} CC</span>
                  </div>
                )) : (
                  <p className="rounded-lg border border-white/10 bg-black/20 p-3 text-sm text-gray-400">
                    {pick("Clasamentul apare după primele scanări.", "The leaderboard appears after the first scans.")}
                  </p>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.055] p-5">
              <p className="inline-flex items-center gap-2 text-sm font-black text-cyan-100">
                <Users size={17} />
                {pick("Invită prieteni", "Invite friends")}
              </p>
              <h2 className="mt-2 text-2xl font-black">
                {pick("100 CeCoins pentru fiecare cont confirmat.", "100 CeCoins for each verified account.")}
              </h2>
              <p className="mt-3 text-sm leading-6 text-gray-300">
                {pick(
                  "Codul tău de invitație este în dashboard. Prietenii ajută catalogul să crească, iar tu primești recompensa automat.",
                  "Your invite code is in the dashboard. Friends help the catalog grow, and you receive the reward automatically."
                )}
              </p>
              <Link
                href="/dashboard"
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-white/15 px-5 py-3 font-black text-white hover:bg-white/10"
              >
                <Gift size={18} />
                {pick("Vezi codul", "See code")}
              </Link>
            </div>
          </div>
        </section>

        {catalogMission && (
          <section className="mt-8 rounded-2xl border border-white/10 bg-black/20 p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="inline-flex items-center gap-2 text-sm font-black text-cyan-200">
                  <CheckCircle2 size={17} />
                  {pick("Misiunea catalogului", "Catalog mission")}
                </p>
                <h2 className="mt-2 text-2xl font-black">{catalogMission.title}</h2>
                <p className="mt-2 text-sm leading-6 text-gray-400">{catalogMission.description}</p>
              </div>
              <Link
                href="/submit-product"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-200 px-5 py-3 font-black text-black hover:bg-white"
              >
                <Clock3 size={18} />
                {pick("Trimite produs", "Submit product")}
              </Link>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

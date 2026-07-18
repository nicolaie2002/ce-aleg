"use client";

import { useSyncExternalStore } from "react";
import Link from "next/link";
import { RefreshCw, Wifi, WifiOff } from "lucide-react";
import { useLocale } from "../components/LocaleProvider";

function subscribeToOnlineStatus(onStoreChange) {
  window.addEventListener("online", onStoreChange);
  window.addEventListener("offline", onStoreChange);

  return () => {
    window.removeEventListener("online", onStoreChange);
    window.removeEventListener("offline", onStoreChange);
  };
}

function getOnlineStatus() {
  return navigator.onLine;
}

export function OfflineContent() {
  const { pick } = useLocale();
  const online = useSyncExternalStore(subscribeToOnlineStatus, getOnlineStatus, () => true);

  return (
    <main className="ce-shell ce-page flex min-h-screen items-center justify-center text-white p-4">
      <section className="w-full max-w-xl rounded-lg border border-white/15 bg-black/45 p-7 text-center">
        {online ? (
          <Wifi aria-hidden="true" className="mx-auto text-emerald-300" size={48} />
        ) : (
          <WifiOff aria-hidden="true" className="mx-auto text-cyan-300" size={48} />
        )}
        <h1 className="mt-5 text-3xl font-black">
          {online
            ? pick("Conexiunea a revenit", "You are back online")
            : pick("Momentan ești offline", "You are currently offline")}
        </h1>
        <p className="mt-3 text-white/70">
          {online
            ? pick(
                "Poți reveni în aplicație și continua de unde ai rămas.",
                "You can return to the app and continue where you left off."
              )
            : pick(
                "Reconectează-te pentru scanări, catalog și datele contului. Nu păstrăm răspunsuri private în cache.",
                "Reconnect to scan products, browse the catalog and access your account. Private responses are not stored in the cache."
              )}
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100 transition-colors"
        >
          <RefreshCw aria-hidden="true" size={18} />
          {pick("Reîncearcă", "Try again")}
        </Link>
      </section>
    </main>
  );
}

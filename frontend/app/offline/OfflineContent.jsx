"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RefreshCw, WifiOff } from "lucide-react";

export function OfflineContent() {
  const [online, setOnline] = useState(typeof navigator !== "undefined" ? navigator.onLine : true);

  useEffect(() => {
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (online) {
    return <Link href="/" className="ce-btn-primary">Reîncearcă / Try again</Link>;
  }

  return (
    <main className="ce-shell ce-page flex min-h-screen items-center justify-center text-white p-4">
      <section className="w-full max-w-xl rounded-lg border border-white/15 bg-black/45 p-7 text-center">
        <WifiOff aria-hidden="true" className="mx-auto text-cyan-300" size={48} />
        <h1 className="mt-5 text-3xl font-black">Momentan ești offline</h1>
        <p className="mt-3 text-white/70">
          Reconectează-te pentru scanări, catalog și datele contului. Nu păstrăm răspunsuri private în cache.
        </p>
        <p className="mt-2 text-sm text-white/55">
          You are offline. Reconnect to scan products and access your account.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100 transition-colors"
        >
          <RefreshCw aria-hidden="true" size={18} />
          Reîncearcă / Try again
        </Link>
      </section>
    </main>
  );
}
import Link from "next/link";
import { RefreshCcw, ScanLine } from "lucide-react";

export const metadata = {
  title: "Offline",
  robots: { index: false, follow: false },
};

export default function OfflinePage() {
  return (
    <main className="ce-shell ce-page flex min-h-screen items-center justify-center text-white">
      <section className="w-full max-w-xl rounded-lg border border-white/15 bg-black/45 p-7 text-center">
        <ScanLine aria-hidden="true" className="mx-auto text-cyan-200" size={42} />
        <h1 className="mt-5 text-3xl font-black">Momentan ești offline</h1>
        <p className="mt-3 text-white/70">
          Reconectează-te pentru scanări, catalog și datele contului. Nu păstrăm răspunsuri private în cache.
        </p>
        <p className="mt-2 text-sm text-white/55">
          You are offline. Reconnect to scan products and access your account.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 font-black text-black hover:bg-cyan-100"
        >
          <RefreshCcw aria-hidden="true" size={18} />
          Reîncearcă / Try again
        </Link>
      </section>
    </main>
  );
}

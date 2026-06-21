export default function Loading() {
  return (
    <main className="min-h-screen text-white">
      <section className="ce-shell ce-page">
        <div className="mx-auto max-w-2xl rounded-2xl border border-white/10 bg-white/[0.04] p-8 shadow-2xl">
          <div className="h-3 w-28 animate-pulse rounded-full bg-cyan-200/50" />
          <div className="mt-5 h-9 w-3/4 animate-pulse rounded-lg bg-white/12" />
          <div className="mt-4 space-y-3">
            <div className="h-4 w-full animate-pulse rounded bg-white/10" />
            <div className="h-4 w-5/6 animate-pulse rounded bg-white/10" />
          </div>
          <div className="mt-7 h-12 w-44 animate-pulse rounded-lg bg-white/14" />
        </div>
      </section>
    </main>
  );
}

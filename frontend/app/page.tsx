import Link from "next/link";

export default function HomePage() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#0a1018] px-6 py-10">
      <div className="pointer-events-none absolute inset-0 opacity-45 [background-image:linear-gradient(to_right,rgba(95,118,150,0.08)_1px,transparent_1px),linear-gradient(to_bottom,rgba(95,118,150,0.08)_1px,transparent_1px)] [background-size:38px_38px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(30,144,255,0.12),transparent_42%)]" />

      <section className="font-satoshi fade-in-enter relative w-full max-w-[900px] rounded-2xl border border-slate-400/20 bg-[#0f1722]/78 p-8 text-center shadow-[0_24px_80px_rgba(2,8,18,0.6)] backdrop-blur-xl md:p-12">
        <h1 className="text-6xl font-bold tracking-[0.06em] text-slate-100 md:text-[88px] md:leading-[0.98]">
          Adalyse
        </h1>

        <p className="mt-4 text-base font-medium tracking-[0.02em] text-cyan-200 md:text-2xl">
          Competitive Creative Intelligence for Growth Teams
        </p>

        <p className="mx-auto mt-6 max-w-3xl text-sm leading-relaxed text-slate-300 md:text-base">
          Track active competitor creatives. Detect message shifts. Surface experimentation velocity. Convert weekly signals into
          decisive action.
        </p>

        <div className="mx-auto mt-8 grid max-w-3xl grid-cols-2 gap-x-6 gap-y-2 border-y border-slate-500/30 py-4 text-[11px] uppercase tracking-[0.08em] text-slate-300 md:grid-cols-4 md:text-xs">
          <span>AI-Native Architecture</span>
          <span>Real-Time Meta Scraping</span>
          <span>Weekly Intelligence Briefs</span>
          <span>Competitive Gap Detection</span>
        </div>

        <div className="mt-9">
          <Link
            href="/dashboard"
            className="inline-flex items-center rounded-md border border-cyan-300/45 bg-cyan-400/16 px-6 py-3 text-sm font-semibold tracking-[0.03em] text-cyan-100 transition duration-200 hover:border-cyan-200/80 hover:bg-cyan-300/22 hover:shadow-[0_0_28px_rgba(34,211,238,0.25)]"
          >
            Enter Intelligence Console
          </Link>
        </div>
      </section>

      <div className="pointer-events-none absolute bottom-5 right-5 rounded-lg border border-slate-500/30 bg-slate-900/60 px-4 py-3 text-right backdrop-blur-md md:bottom-7 md:right-7">
        <div className="flex flex-col items-end">
          <p className="text-base font-semibold tracking-[0.05em] text-cyan-100 md:text-lg">Mosaic Wellness</p>
          <div className="mt-2 h-px w-full bg-slate-500/35" />
          <p className="mt-2 text-[11px] font-medium tracking-[0.05em] text-slate-300">
            Bebodywise &nbsp;&nbsp; Man Matters &nbsp;&nbsp; Little Joys
          </p>
        </div>
      </div>
    </main>
  );
}

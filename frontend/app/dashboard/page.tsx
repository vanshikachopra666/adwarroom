"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { DashboardFilters, getCompetitors, getDashboard, getLiveInsights, getWeeklyBrief, getWeeklyBriefPdfUrl } from "@/lib/api";
import { DashboardPayload, LiveInsightsPayload, WeeklyBriefPayload } from "@/lib/types";

const mosaicBrands = [
  { value: "bebodywise", label: "Bebodywise" },
  { value: "manmatters", label: "Man matters" },
  { value: "littlejoys", label: "Little joys" },
];
const creativeFormats = ["UGC", "Studio", "Doctor-backed", "Influencer", "Meme-style", "Product demo"];
const themes = [
  "Authority",
  "Social proof",
  "Problem agitation",
  "Discount push",
  "Subscription",
  "Ingredient science",
  "Transformation",
  "Community storytelling",
];
const themeColors: Record<string, string> = {
  Authority: "#8ff6ec",
  "Social proof": "#8fd9ff",
  "Problem agitation": "#67c4ff",
  "Discount push": "#50b3ff",
  Subscription: "#70dfd7",
  "Ingredient science": "#95d8ff",
  Transformation: "#58b4c9",
  "Community storytelling": "#c8f4ff",
};

const fetcher = ([_, filters]: [string, Record<string, string>]) => getDashboard(filters);
const chartTooltipStyle = {
  background: "rgba(6, 29, 53, 0.96)",
  border: "1px solid rgba(151, 211, 255, 0.45)",
  borderRadius: "10px",
  boxShadow: "0 18px 32px rgba(3, 22, 42, 0.45)",
};
const shortWeekLabel = (value: string | number) => {
  const raw = String(value ?? "");
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="panel p-4 animate-rise">
      <div className="mb-2 h-1 w-12 rounded-full bg-gradient-to-r from-cyan-300 to-sky-300" />
      <p className="text-xs uppercase tracking-[0.15em] text-cyan-100/75">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function heatColorByRate(rate: number): string {
  // Use an absolute benchmark so colors stay stable even with a single competitor filter.
  // 25%+ new-ad velocity is treated as very hot.
  const n = Math.max(0, Math.min(1, rate / 0.25));
  const hue = 120 * (1 - n); // green -> red
  return `hsl(${hue} 85% 52%)`;
}

export default function Page() {
  const toIsoDate = (d: Date) => d.toISOString().slice(0, 10);
  const today = new Date();
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(today.getDate() - 7);

  const [mosaicBrand, setMosaicBrand] = useState("bebodywise");
  const [competitor, setCompetitor] = useState("");
  const [startDate, setStartDate] = useState(toIsoDate(sevenDaysAgo));
  const [endDate, setEndDate] = useState(toIsoDate(today));
  const [creativeFormat, setCreativeFormat] = useState("");
  const [messageTheme, setMessageTheme] = useState("");
  const [status, setStatus] = useState<"active" | "inactive" | "all">("all");

  const filters = useMemo(
    () => ({
      mosaic_brand: mosaicBrand,
      competitor: competitor || "",
      start_date: startDate || "",
      end_date: endDate || "",
      creative_format: creativeFormat || "",
      message_theme: messageTheme || "",
      status,
    }),
    [mosaicBrand, competitor, startDate, endDate, creativeFormat, messageTheme, status],
  );

  const { data, isLoading, error } = useSWR<DashboardPayload>(["dashboard", filters], fetcher, {
    refreshInterval: 60_000,
  });

  const { data: competitors } = useSWR(["competitors", mosaicBrand], ([_, brand]: [string, string]) => getCompetitors(brand));
  const { data: brief } = useSWR<WeeklyBriefPayload>(["brief", mosaicBrand], ([_, brand]: [string, string]) => getWeeklyBrief(brand));
  const { data: liveInsights } = useSWR<LiveInsightsPayload>(["live-insights", filters], ([_, f]: [string, DashboardFilters]) => getLiveInsights(f), {
    refreshInterval: 30_000,
  });

  const themeStack = useMemo(() => {
    if (!data?.theme_trend?.length) return [];
    return data.theme_trend;
  }, [data]);
  return (
    <main className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 md:px-8">
      {error && (
        <div className="rounded-lg border border-amber-300/35 bg-amber-200/10 px-4 py-3 text-sm text-amber-100">
          Live API is temporarily unavailable. Showing available dashboard data.
        </div>
      )}
      <section className="panel p-6">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="inline-flex items-center rounded-full border border-cyan-100/35 bg-cyan-100/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-cyan-100/90">
              Adalyse
            </p>
            <h1 className="mt-3 font-[var(--font-heading)] text-3xl font-semibold text-white md:text-4xl">
              Meta Ad Competitor Tracker
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-cyan-100/80 md:text-[15px]">
              Live monitoring for creative trends, messaging shifts, and competitor testing velocity across Mosaic categories.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="rounded-full border border-cyan-100/25 bg-cyan-100/10 px-2.5 py-1 text-[11px] text-cyan-50">Live insights</span>
              <span className="rounded-full border border-cyan-100/25 bg-cyan-100/10 px-2.5 py-1 text-[11px] text-cyan-50">Weekly briefing</span>
              <span className="rounded-full border border-cyan-100/25 bg-cyan-100/10 px-2.5 py-1 text-[11px] text-cyan-50">Opportunity detection</span>
            </div>
          </div>
          <a
            href={getWeeklyBriefPdfUrl(mosaicBrand)}
            className="rounded-lg bg-gradient-to-r from-cyan-300 to-sky-300 px-4 py-2 text-sm font-medium text-slate-950 transition hover:brightness-110"
          >
            Download Weekly Brief PDF
          </a>
        </div>

        <div className="rounded-xl border border-cyan-100/20 bg-cyan-100/5 p-3">
          <p className="mb-3 text-[11px] uppercase tracking-[0.1em] text-cyan-100/70">Dashboard Filters</p>
          <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-7">
          <select
            value={mosaicBrand}
            onChange={(e) => {
              setMosaicBrand(e.target.value);
              setCompetitor("");
            }}
          >
            {mosaicBrands.map((brand) => (
              <option key={brand.value} value={brand.value}>
                {brand.label}
              </option>
            ))}
          </select>
          <select value={competitor} onChange={(e) => setCompetitor(e.target.value)}>
            <option value="">All competitors</option>
            {(competitors || []).map((comp) => (
              <option key={comp.id} value={comp.name}>
                {comp.name}
              </option>
            ))}
          </select>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          <select value={creativeFormat} onChange={(e) => setCreativeFormat(e.target.value)}>
            <option value="">All formats</option>
            {creativeFormats.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
          <select value={messageTheme} onChange={(e) => setMessageTheme(e.target.value)}>
            <option value="">All themes</option>
            {themes.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
          <select value={status} onChange={(e) => setStatus(e.target.value as "active" | "inactive" | "all")}>
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
        <KpiCard label="Total Competitors" value={data?.overview?.total_competitors ?? 0} />
        <KpiCard label="Total Active Ads" value={data?.overview?.total_active_ads ?? 0} />
        <KpiCard label="% Video" value={`${data?.overview?.video_percentage ?? 0}%`} />
        <KpiCard label="% UGC" value={`${data?.overview?.ugc_percentage ?? 0}%`} />
        <KpiCard label="Avg Ad Age" value={`${data?.overview?.avg_ad_age ?? 0} days`} />
        <KpiCard label="Highest Longevity" value={data?.overview?.highest_longevity_brand ?? "N/A"} />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-4">
          <h2 className="section-title">Creative Format Trend</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data?.format_trend || []}>
                <CartesianGrid stroke="#2a4a5d" strokeDasharray="3 3" />
                <XAxis dataKey="week" stroke="#d6f8ff" />
                <YAxis stroke="#d6f8ff" />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  cursor={{ stroke: "#8fd5ff", strokeWidth: 1 }}
                  labelStyle={{ color: "#f4fbff", fontFamily: "var(--font-heading)", fontWeight: 600, fontSize: 12 }}
                  itemStyle={{ color: "#d7f0ff", fontFamily: "var(--font-body)", fontSize: 12 }}
                />
                <Legend />
                <Line dataKey="video" stroke="#7ff0e7" strokeWidth={2.5} />
                <Line dataKey="image" stroke="#90e8ff" strokeWidth={2.5} />
                <Line dataKey="carousel" stroke="#b7dcff" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel p-4">
          <h2 className="section-title">Messaging Theme Trend</h2>
          <div className="mb-3 flex flex-wrap gap-2">
            {themes.map((theme) => (
              <span
                key={`legend-${theme}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-cyan-100/20 bg-cyan-100/10 px-2.5 py-1 text-[11px] text-cyan-50"
              >
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: themeColors[theme] }} />
                {theme}
              </span>
            ))}
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={themeStack} barCategoryGap={20}>
                <CartesianGrid stroke="#2a4a5d" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="week" stroke="#d6f8ff" tickFormatter={shortWeekLabel} tick={{ fontSize: 11 }} />
                <YAxis stroke="#d6f8ff" />
                <Tooltip
                  contentStyle={chartTooltipStyle}
                  cursor={{ fill: "rgba(143, 213, 255, 0.15)" }}
                  labelStyle={{ color: "#f4fbff", fontFamily: "var(--font-heading)", fontWeight: 600, fontSize: 12 }}
                  itemStyle={{ color: "#d7f0ff", fontFamily: "var(--font-body)", fontSize: 12 }}
                  labelFormatter={shortWeekLabel}
                />
                {themes.map((theme, idx) => (
                  <Bar
                    key={theme}
                    dataKey={theme}
                    stackId="theme"
                    fill={themeColors[theme]}
                    radius={idx === themes.length - 1 ? [6, 6, 0, 0] : [0, 0, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="panel overflow-hidden p-4 lg:col-span-1">
          <h2 className="section-title">Longevity Leaderboard</h2>
          <div className="space-y-2">
            {(data?.longevity || []).map((row) => (
              <div key={row.competitor} className="rounded-lg border border-cyan-100/20 bg-cyan-100/5 p-3">
                <div className="flex items-center justify-between text-sm">
                  <span>{row.competitor}</span>
                  <span>{(row.longevity_ratio * 100).toFixed(1)}%</span>
                </div>
                <p className="mt-1 text-xs text-cyan-100/70">
                  {row.long_running_ads} long-running / {row.total_active_ads} active
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel p-4 lg:col-span-1">
          <h2 className="section-title">Experimentation Heatmap</h2>
          <div className="space-y-3">
            {(data?.experimentation || []).length === 0 && <p className="text-sm text-cyan-100/70">No experimentation data yet.</p>}
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {(data?.experimentation || []).map((entry) => (
                <div
                  key={entry.competitor}
                  className="rounded-lg border border-cyan-100/20 p-3"
                  style={{ backgroundColor: heatColorByRate(entry.experimentation_rate) }}
                  title={`${entry.competitor}: ${(entry.experimentation_rate * 100).toFixed(1)}% new-ad velocity`}
                >
                  <p className="truncate text-xs font-semibold text-slate-950">{entry.competitor}</p>
                  <p className="mt-2 text-xl font-semibold text-slate-950">{(entry.experimentation_rate * 100).toFixed(1)}%</p>
                  <p className="text-[11px] text-slate-900/80">
                    {entry.new_ads_count} new / {entry.total_active_ads} active
                  </p>
                </div>
              ))}
            </div>
            <div className="pt-2">
              <div className="mb-1 text-[10px] uppercase tracking-[0.08em] text-cyan-100/70">Low to high intensity</div>
              <div className="h-2 rounded-full bg-gradient-to-r from-green-500 via-yellow-400 via-orange-400 to-red-500" />
              <div className="mt-1 flex justify-between text-[10px] text-cyan-100/65">
                <span>0%</span>
                <span>12.5%</span>
                <span>25%+</span>
              </div>
            </div>
          </div>
        </div>

        <div className="panel p-4 lg:col-span-1">
          <h2 className="section-title">Messaging Shift Alerts</h2>
          <div className="space-y-2">
            {(data?.shift_alerts || []).length === 0 && <p className="text-sm text-cyan-100/70">No significant shifts detected.</p>}
            {(data?.shift_alerts || []).map((alert) => (
              <div key={alert.theme} className="rounded-lg border border-cyan-100/20 bg-cyan-100/5 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-white">{alert.theme}</p>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] ${
                      alert.severity === "critical" ? "bg-rose-300/20 text-rose-200" : "bg-amber-300/20 text-amber-200"
                    }`}
                  >
                    {alert.severity || "watch"}
                  </span>
                </div>
                <p className={`mt-1 text-xs ${alert.direction === "up" ? "text-cyan-200" : "text-sky-200"}`}>
                  {alert.direction === "up" ? "↑" : "↓"} {alert.deviation}% vs 4-week baseline
                </p>
                <p className="mt-1 text-[11px] text-cyan-100/70">
                  Current {alert.current_percentage}% ({alert.current_count ?? 0}) vs baseline {alert.baseline_percentage}% ({alert.baseline_count ?? 0})
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-4 lg:col-span-2">
          <h2 className="section-title">Live Actionable Insights</h2>
          <div className="grid gap-2">
            {(liveInsights?.insights || []).length === 0 && (
              <p className="text-sm text-cyan-100/70">Insights will appear after ad snapshots are available.</p>
            )}
            {(liveInsights?.insights || []).map((insight, idx) => (
              <div key={`${idx}-${insight.slice(0, 24)}`} className="rounded-lg border border-cyan-200/35 bg-gradient-to-r from-cyan-300/15 to-sky-300/10 p-3 text-sm text-white">
                {insight}
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-cyan-100/55">
            Auto-refreshes every 30 seconds for current filters.
          </p>
        </div>

        <div className="panel p-4">
          <h2 className="section-title">Opportunity Gap Panel</h2>
          <div className="space-y-2">
            {(data?.opportunities || []).length === 0 && <p className="text-sm text-cyan-100/70">No gaps detected yet.</p>}
            {(data?.opportunities || []).map((opp, idx) => (
              <div key={`${opp.name}-${idx}`} className="rounded-lg border border-cyan-200/30 bg-cyan-200/10 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-cyan-100">{opp.type}</p>
                  <p className="rounded-full bg-cyan-100/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-cyan-100/90">
                    {opp.dimension.replace("_", " ")}
                  </p>
                </div>
                <p className="mt-1 text-sm text-white">{opp.name}</p>
                <p className="mt-1 text-xs text-cyan-100/80">Usage: {opp.usage_percentage}%</p>
                {opp.insight && <p className="mt-2 text-xs text-cyan-50/90">{opp.insight}</p>}
                {opp.action && <p className="mt-2 text-xs font-medium text-white">Action: {opp.action}</p>}
              </div>
            ))}
          </div>
        </div>

        <div className="panel p-4">
          <h2 className="section-title">Weekly AI Brief</h2>
          {isLoading && <p className="text-sm text-cyan-100/70">Loading summary...</p>}
          {!brief?.report && (
            <article className="max-h-72 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-cyan-50/95">
              {brief?.brief || "No brief available yet. Run ingestion and analytics first."}
            </article>
          )}
          {brief?.report && (
            <div className="space-y-3 text-sm text-cyan-50/95">
              <div className="rounded-lg border border-cyan-100/20 bg-cyan-100/10 p-3">
                <p className="text-xs uppercase tracking-[0.1em] text-cyan-100/70">Executive Snapshot</p>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <p>Competitors: {brief.report.overview.total_competitors}</p>
                  <p>Active ads: {brief.report.overview.total_active_ads}</p>
                  <p>Video share: {brief.report.overview.video_percentage}%</p>
                  <p>UGC share: {brief.report.overview.ugc_percentage}%</p>
                </div>
              </div>

              <div className="rounded-lg border border-cyan-100/20 bg-cyan-100/10 p-3">
                <p className="text-xs uppercase tracking-[0.1em] text-cyan-100/70">Priority Actions</p>
                <div className="mt-2 space-y-1">
                  {(brief.report.priority_actions || []).slice(0, 4).map((item, idx) => (
                    <p key={`${idx}-${item}`} className="text-xs leading-relaxed">
                      {idx + 1}. {item}
                    </p>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-cyan-100/20 bg-cyan-100/10 p-3">
                <p className="text-xs uppercase tracking-[0.1em] text-cyan-100/70">Narrative Summary</p>
                <article className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-cyan-50/95">
                  {brief.report.narrative || brief.brief}
                </article>
              </div>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

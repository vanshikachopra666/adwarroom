import { DashboardPayload, Competitor, LiveInsightsPayload, WeeklyBriefPayload } from "@/lib/types";

const DEFAULT_PROD_API_URL = "https://competitor-ad-war-room-api.onrender.com/api/v1";
const API_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (process.env.NODE_ENV === "production" ? DEFAULT_PROD_API_URL : "http://127.0.0.1:8000/api/v1");
const BASE_PATH = process.env.NODE_ENV === "production" ? "/adwarroom" : "";
const DEFAULT_BRAND = "bebodywise";
const SHOULD_PREFER_MOCK_IN_PROD = process.env.NODE_ENV === "production" && !process.env.NEXT_PUBLIC_API_BASE_URL;
const KNOWN_THEMES = [
  "Authority",
  "Social proof",
  "Problem agitation",
  "Discount push",
  "Subscription",
  "Ingredient science",
  "Transformation",
  "Community storytelling",
];
const KNOWN_FORMATS = ["UGC", "Studio", "Doctor-backed", "Influencer", "Meme-style", "Product demo"];

type MockAdRow = {
  competitor_name: string;
  mosaic_brand: string;
  ad_id: string;
  media_type: string;
  start_date?: string | null;
  end_date?: string | null;
  is_active: boolean;
  scraped_at: string;
  creative_format?: string | null;
  message_theme?: string | null;
  funnel_stage?: string | null;
  emotional_tone?: string | null;
};

const mockAdsCache = new Map<string, Promise<MockAdRow[]>>();

export type DashboardFilters = {
  mosaic_brand?: string;
  competitor?: string;
  start_date?: string;
  end_date?: string;
  creative_format?: string;
  message_theme?: string;
  status?: "active" | "inactive" | "all";
};

function withQuery(path: string, params: Record<string, string | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) search.set(key, value);
  });
  return `${API_URL}${path}?${search.toString()}`;
}

function brandOrDefault(mosaicBrand?: string): string {
  return mosaicBrand || DEFAULT_BRAND;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function weekStartIso(d: Date): string {
  const copy = new Date(d);
  const day = copy.getUTCDay();
  const diff = day === 0 ? -6 : 1 - day;
  copy.setUTCDate(copy.getUTCDate() + diff);
  return copy.toISOString().slice(0, 10);
}

function daysBetween(a: Date, b: Date): number {
  const ms = Math.max(0, b.getTime() - a.getTime());
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

async function loadMockAds(brand: string): Promise<MockAdRow[]> {
  const key = brandOrDefault(brand);
  if (!mockAdsCache.has(key)) {
    mockAdsCache.set(
      key,
      fetch(`${BASE_PATH}/mock/ads-${key}.json`, { cache: "no-store" }).then((res) => {
        if (!res.ok) throw new Error("Failed to fetch fallback ad dataset");
        return res.json();
      }),
    );
  }
  return mockAdsCache.get(key)!;
}

function buildInsights(payload: DashboardPayload): string[] {
  const overview = payload.overview || ({} as DashboardPayload["overview"]);
  const insights: string[] = [];
  const topL = (payload.longevity || [])[0];
  const topE = (payload.experimentation || [])[0];
  const topShift = (payload.shift_alerts || [])[0];
  const topOpp = (payload.opportunities || [])[0];

  if (topL?.competitor) {
    insights.push(
      `${topL.competitor} is retaining winners with a ${(topL.longevity_ratio * 100).toFixed(1)}% longevity ratio, so duplicate your top 2 performers into fresh hooks this week.`,
    );
  }
  if (topE?.competitor) {
    insights.push(
      `${topE.competitor} is testing fastest at ${(topE.experimentation_rate * 100).toFixed(1)}%, so ship at least ${Math.max(3, topE.new_ads_count || 0)} net-new ads in the next 7 days.`,
    );
  }
  if ((overview.video_percentage || 0) < 40) {
    insights.push(
      `Video share is ${overview.video_percentage || 0}%, so raise it to 40%+ by converting your strongest static concepts into short video cuts.`,
    );
  }
  if (topShift?.theme) {
    insights.push(
      `${topShift.theme} moved ${Math.abs(topShift.deviation).toFixed(1)} points vs baseline, so adjust next-week messaging mix accordingly.`,
    );
  }
  if (topOpp?.name) {
    insights.push(
      `${topOpp.type} detected in ${topOpp.name} at ${topOpp.usage_percentage}%, so prioritize this gap in your next creative sprint.`,
    );
  }
  return insights.slice(0, 5);
}

async function computeDashboardFromMock(filters: DashboardFilters): Promise<DashboardPayload> {
  const brand = brandOrDefault(filters.mosaic_brand);
  const rows = await loadMockAds(brand);
  const now = new Date();
  const start = parseDate(filters.start_date);
  const end = parseDate(filters.end_date);

  const allCompetitors = Array.from(new Set(rows.map((r) => r.competitor_name)));
  const filtered = rows.filter((r) => {
    if (filters.competitor && r.competitor_name !== filters.competitor) return false;
    if (filters.status === "active" && !r.is_active) return false;
    if (filters.status === "inactive" && r.is_active) return false;
    if (filters.creative_format && (r.creative_format || "") !== filters.creative_format) return false;
    if (filters.message_theme && (r.message_theme || "") !== filters.message_theme) return false;
    const scraped = parseDate(r.scraped_at);
    if (!scraped) return false;
    if (start && scraped < new Date(`${start.toISOString().slice(0, 10)}T00:00:00.000Z`)) return false;
    if (end && scraped > new Date(`${end.toISOString().slice(0, 10)}T23:59:59.999Z`)) return false;
    return true;
  });

  const total = filtered.length || 1;
  const activeRows = filtered.filter((r) => r.is_active);
  const videoPct = Math.round((10000 * filtered.filter((r) => r.media_type === "video").length) / total) / 100;
  const ugcPct = Math.round((10000 * filtered.filter((r) => (r.creative_format || "") === "UGC").length) / total) / 100;
  const ages = filtered
    .map((r) => parseDate(r.start_date || undefined))
    .filter((d): d is Date => !!d)
    .map((d) => daysBetween(d, now));
  const avgAdAge = ages.length ? Math.round((100 * ages.reduce((a, b) => a + b, 0)) / ages.length) / 100 : 0;

  const byWeekFormat: Record<string, { video: number; image: number; carousel: number }> = {};
  const byWeekTheme: Record<string, Record<string, number>> = {};
  filtered.forEach((r) => {
    const scraped = parseDate(r.scraped_at);
    if (!scraped) return;
    const wk = weekStartIso(scraped);
    byWeekFormat[wk] ??= { video: 0, image: 0, carousel: 0 };
    if (r.media_type === "video") byWeekFormat[wk].video += 1;
    else if (r.media_type === "carousel") byWeekFormat[wk].carousel += 1;
    else byWeekFormat[wk].image += 1;

    if (r.message_theme) {
      byWeekTheme[wk] ??= {};
      byWeekTheme[wk][r.message_theme] = (byWeekTheme[wk][r.message_theme] || 0) + 1;
    }
  });

  const perComp: Record<string, MockAdRow[]> = {};
  filtered.forEach((r) => {
    perComp[r.competitor_name] ??= [];
    perComp[r.competitor_name].push(r);
  });

  const longevity = Object.entries(perComp).map(([competitor, items]) => {
    const active = items.filter((r) => r.is_active);
    const longRunning = active.filter((r) => {
      const sd = parseDate(r.start_date || undefined);
      return sd ? daysBetween(sd, now) > 60 : false;
    }).length;
    const totalActive = active.length;
    return {
      competitor,
      long_running_ads: longRunning,
      total_active_ads: totalActive,
      longevity_ratio: totalActive ? Number((longRunning / totalActive).toFixed(4)) : 0,
    };
  });

  const experimentation = Object.entries(perComp).map(([competitor, items]) => {
    const active = items.filter((r) => r.is_active);
    const newAds = items.filter((r) => {
      const sd = parseDate(r.start_date || undefined);
      return sd ? daysBetween(sd, now) <= 14 : false;
    }).length;
    const totalActive = active.length;
    return {
      competitor,
      new_ads_count: newAds,
      total_active_ads: totalActive,
      experimentation_rate: totalActive ? Number((newAds / totalActive).toFixed(4)) : 0,
    };
  });

  const shiftCurrentStart = new Date(now);
  shiftCurrentStart.setUTCDate(now.getUTCDate() - 7);
  const shiftBaseStart = new Date(now);
  shiftBaseStart.setUTCDate(now.getUTCDate() - 35);
  const shiftCurrentRows = filtered.filter((r) => {
    const d = parseDate(r.scraped_at);
    return d && d >= shiftCurrentStart;
  });
  const shiftBaseRows = filtered.filter((r) => {
    const d = parseDate(r.scraped_at);
    return d && d >= shiftBaseStart && d < shiftCurrentStart;
  });
  const currentThemeCounts: Record<string, number> = {};
  const baseThemeCounts: Record<string, number> = {};
  shiftCurrentRows.forEach((r) => {
    if (!r.message_theme) return;
    currentThemeCounts[r.message_theme] = (currentThemeCounts[r.message_theme] || 0) + 1;
  });
  shiftBaseRows.forEach((r) => {
    if (!r.message_theme) return;
    baseThemeCounts[r.message_theme] = (baseThemeCounts[r.message_theme] || 0) + 1;
  });
  const ct = Math.max(1, shiftCurrentRows.length);
  const bt = Math.max(1, shiftBaseRows.length);
  const allThemes = Array.from(new Set([...Object.keys(currentThemeCounts), ...Object.keys(baseThemeCounts)]));
  const shiftAlerts = allThemes
    .map((theme) => {
      const currentPct = Number(((100 * (currentThemeCounts[theme] || 0)) / ct).toFixed(2));
      const basePct = Number(((100 * (baseThemeCounts[theme] || 0)) / bt).toFixed(2));
      const deviation = Number((currentPct - basePct).toFixed(2));
      return {
        theme,
        current_percentage: currentPct,
        baseline_percentage: basePct,
        deviation,
        direction: deviation >= 0 ? "up" : "down",
        severity: (Math.abs(deviation) >= 20 ? "critical" : "watch") as "critical" | "watch",
      };
    })
    .sort((a, b) => Math.abs(b.deviation) - Math.abs(a.deviation))
    .slice(0, 4);

  const themeCounts: Record<string, number> = {};
  const formatCounts: Record<string, number> = {};
  filtered.forEach((r) => {
    if (r.message_theme) themeCounts[r.message_theme] = (themeCounts[r.message_theme] || 0) + 1;
    if (r.creative_format) formatCounts[r.creative_format] = (formatCounts[r.creative_format] || 0) + 1;
  });
  const opportunities = [
    ...KNOWN_THEMES.map((theme) => {
      const pct = Number(((100 * (themeCounts[theme] || 0)) / total).toFixed(2));
      return {
        type: pct < 10 ? "Theme Whitespace" : "",
        dimension: "message_theme",
        name: theme,
        usage_percentage: pct,
        insight: `${theme} appears in only ${pct}% of creatives in this view.`,
        action: `Launch 2 focused creatives on ${theme} and compare against control.`,
        priority: pct < 10 ? 1 : 0,
      };
    }).filter((o) => o.priority > 0),
    ...KNOWN_FORMATS.map((fmt) => {
      const pct = Number(((100 * (formatCounts[fmt] || 0)) / total).toFixed(2));
      return {
        type: pct === 0 ? "Untapped Creative Format" : pct < 6 ? "Low-Saturation Creative Format" : "",
        dimension: "creative_format",
        name: fmt,
        usage_percentage: pct,
        insight: `${fmt} usage is ${pct}% in this filtered view.`,
        action: `Add at least 2 ${fmt} variants this week.`,
        priority: pct === 0 ? 3 : pct < 6 ? 1 : 0,
      };
    }).filter((o) => o.priority > 0),
  ]
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 8);

  const sortedLongevity = longevity.sort((a, b) => b.longevity_ratio - a.longevity_ratio);
  const highestLongevityBrand = sortedLongevity[0]?.competitor || "N/A";

  return {
    overview: {
      total_competitors: filters.competitor ? 1 : allCompetitors.length,
      total_active_ads: activeRows.length,
      video_percentage: videoPct,
      ugc_percentage: ugcPct,
      avg_ad_age: avgAdAge,
      highest_longevity_brand: highestLongevityBrand,
    },
    format_trend: Object.entries(byWeekFormat)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([week, values]) => ({ week, ...values })),
    theme_trend: Object.entries(byWeekTheme)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([week, values]) => ({ week, ...values })),
    longevity: sortedLongevity,
    experimentation: experimentation.sort((a, b) => b.experimentation_rate - a.experimentation_rate),
    shift_alerts: shiftAlerts,
    opportunities,
  };
}

async function fetchJsonWithFallback<T>(primaryUrl: string, fallbackPath: string): Promise<T> {
  const fetchFallback = async () => {
    const fallback = await fetch(`${BASE_PATH}${fallbackPath}`, { cache: "no-store" });
    if (!fallback.ok) {
      throw new Error("Failed to fetch dashboard data");
    }
    return fallback.json() as Promise<T>;
  };

  if (SHOULD_PREFER_MOCK_IN_PROD) {
    return fetchFallback();
  }

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const res = await fetch(primaryUrl, { cache: "no-store" });
      if (res.ok) return res.json();
    } catch (_err) {
      // Retry once before fallback.
    }
  }

  return fetchFallback();
}

export async function getDashboard(filters: DashboardFilters): Promise<DashboardPayload> {
  if (SHOULD_PREFER_MOCK_IN_PROD) {
    return computeDashboardFromMock(filters);
  }
  const brand = brandOrDefault(filters.mosaic_brand);
  const competitorSlug = filters.competitor ? slugify(filters.competitor) : "";
  const url = withQuery("/dashboard", {
    mosaic_brand: brand,
    competitor: filters.competitor,
    start_date: filters.start_date,
    end_date: filters.end_date,
    creative_format: filters.creative_format,
    message_theme: filters.message_theme,
    status: filters.status,
  });
  const fallbackPath = competitorSlug ? `/mock/dashboard-${brand}-${competitorSlug}.json` : `/mock/dashboard-${brand}.json`;
  return fetchJsonWithFallback<DashboardPayload>(url, fallbackPath);
}

export async function getLiveInsights(filters: DashboardFilters): Promise<LiveInsightsPayload> {
  if (SHOULD_PREFER_MOCK_IN_PROD) {
    const payload = await computeDashboardFromMock(filters);
    return {
      insights: buildInsights(payload),
      generated_at: new Date().toISOString(),
    };
  }
  const brand = brandOrDefault(filters.mosaic_brand);
  const competitorSlug = filters.competitor ? slugify(filters.competitor) : "";
  const url = withQuery("/insights/live", {
    mosaic_brand: brand,
    competitor: filters.competitor,
    start_date: filters.start_date,
    end_date: filters.end_date,
    creative_format: filters.creative_format,
    message_theme: filters.message_theme,
    status: filters.status,
  });
  const fallbackPath = competitorSlug ? `/mock/live-insights-${brand}-${competitorSlug}.json` : `/mock/live-insights-${brand}.json`;
  return fetchJsonWithFallback<LiveInsightsPayload>(url, fallbackPath);
}

export async function getCompetitors(mosaicBrand?: string): Promise<Competitor[]> {
  const brand = brandOrDefault(mosaicBrand);
  const url = withQuery("/competitors", { mosaic_brand: brand });
  return fetchJsonWithFallback<Competitor[]>(url, `/mock/competitors-${brand}.json`);
}

export async function getWeeklyBrief(mosaicBrand: string): Promise<WeeklyBriefPayload> {
  return fetchJsonWithFallback<WeeklyBriefPayload>(
    `${API_URL}/weekly-brief/${mosaicBrand}`,
    `/mock/weekly-brief-${brandOrDefault(mosaicBrand)}.json`,
  );
}

export function getWeeklyBriefPdfUrl(mosaicBrand: string): string {
  const brand = brandOrDefault(mosaicBrand);
  if (SHOULD_PREFER_MOCK_IN_PROD) {
    return `${BASE_PATH}/mock/weekly-brief-${brand}.pdf`;
  }
  return `${API_URL}/weekly-brief/${brand}/pdf`;
}

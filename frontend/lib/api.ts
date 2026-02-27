import { DashboardPayload, Competitor, LiveInsightsPayload, WeeklyBriefPayload } from "@/lib/types";

const DEFAULT_PROD_API_URL = "https://competitor-ad-war-room-api.onrender.com/api/v1";
const API_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (process.env.NODE_ENV === "production" ? DEFAULT_PROD_API_URL : "http://127.0.0.1:8000/api/v1");
const BASE_PATH = process.env.NODE_ENV === "production" ? "/adwarroom" : "";
const DEFAULT_BRAND = "bebodywise";

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

async function fetchJsonWithFallback<T>(primaryUrl: string, fallbackPath: string): Promise<T> {
  try {
    const res = await fetch(primaryUrl, { cache: "no-store" });
    if (res.ok) return res.json();
  } catch (_err) {
    // Fallback handled below.
  }

  const fallback = await fetch(`${BASE_PATH}${fallbackPath}`, { cache: "no-store" });
  if (!fallback.ok) {
    throw new Error("Failed to fetch dashboard data");
  }
  return fallback.json();
}

export async function getDashboard(filters: DashboardFilters): Promise<DashboardPayload> {
  const brand = brandOrDefault(filters.mosaic_brand);
  const url = withQuery("/dashboard", {
    mosaic_brand: brand,
    competitor: filters.competitor,
    start_date: filters.start_date,
    end_date: filters.end_date,
    creative_format: filters.creative_format,
    message_theme: filters.message_theme,
    status: filters.status,
  });
  return fetchJsonWithFallback<DashboardPayload>(url, `/mock/dashboard-${brand}.json`);
}

export async function getLiveInsights(filters: DashboardFilters): Promise<LiveInsightsPayload> {
  const brand = brandOrDefault(filters.mosaic_brand);
  const url = withQuery("/insights/live", {
    mosaic_brand: brand,
    competitor: filters.competitor,
    start_date: filters.start_date,
    end_date: filters.end_date,
    creative_format: filters.creative_format,
    message_theme: filters.message_theme,
    status: filters.status,
  });
  return fetchJsonWithFallback<LiveInsightsPayload>(url, `/mock/live-insights-${brand}.json`);
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
  return `${API_URL}/weekly-brief/${mosaicBrand}/pdf`;
}

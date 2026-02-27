import { DashboardPayload, Competitor, LiveInsightsPayload, WeeklyBriefPayload } from "@/lib/types";

const DEFAULT_PROD_API_URL = "https://competitor-ad-war-room-api.onrender.com/api/v1";
const API_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (process.env.NODE_ENV === "production" ? DEFAULT_PROD_API_URL : "http://127.0.0.1:8000/api/v1");

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

export async function getDashboard(filters: DashboardFilters): Promise<DashboardPayload> {
  const url = withQuery("/dashboard", {
    mosaic_brand: filters.mosaic_brand,
    competitor: filters.competitor,
    start_date: filters.start_date,
    end_date: filters.end_date,
    creative_format: filters.creative_format,
    message_theme: filters.message_theme,
    status: filters.status,
  });
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch dashboard data");
  return res.json();
}

export async function getLiveInsights(filters: DashboardFilters): Promise<LiveInsightsPayload> {
  const url = withQuery("/insights/live", {
    mosaic_brand: filters.mosaic_brand,
    competitor: filters.competitor,
    start_date: filters.start_date,
    end_date: filters.end_date,
    creative_format: filters.creative_format,
    message_theme: filters.message_theme,
    status: filters.status,
  });
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch live insights");
  return res.json();
}

export async function getCompetitors(mosaicBrand?: string): Promise<Competitor[]> {
  const url = withQuery("/competitors", { mosaic_brand: mosaicBrand });
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch competitors");
  return res.json();
}

export async function getWeeklyBrief(mosaicBrand: string): Promise<WeeklyBriefPayload> {
  const res = await fetch(`${API_URL}/weekly-brief/${mosaicBrand}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch weekly brief");
  return res.json();
}

export function getWeeklyBriefPdfUrl(mosaicBrand: string): string {
  return `${API_URL}/weekly-brief/${mosaicBrand}/pdf`;
}

export type DashboardOverview = {
  total_competitors: number;
  total_active_ads: number;
  video_percentage: number;
  ugc_percentage: number;
  avg_ad_age: number;
  highest_longevity_brand: string;
};

export type DashboardPayload = {
  overview: DashboardOverview;
  format_trend: Array<{ week: string; video: number; image: number; carousel: number }>;
  theme_trend: Array<Record<string, string | number>>;
  longevity: Array<{ competitor: string; long_running_ads: number; total_active_ads: number; longevity_ratio: number }>;
  experimentation: Array<{ competitor: string; new_ads_count: number; total_active_ads: number; experimentation_rate: number }>;
  shift_alerts: Array<{
    theme: string;
    current_percentage: number;
    baseline_percentage: number;
    deviation: number;
    direction: string;
    severity?: "critical" | "watch";
    current_count?: number;
    baseline_count?: number;
  }>;
  opportunities: Array<{
    type: string;
    dimension: string;
    name: string;
    usage_percentage: number;
    insight?: string;
    action?: string;
    priority?: number;
  }>;
};

export type Competitor = {
  id: number;
  name: string;
  mosaic_brand: string;
  facebook_page_id: string;
  justification: string;
  target_audience: string;
  price_tier: string;
  created_at: string;
};

export type LiveInsightsPayload = {
  insights: string[];
  generated_at: string;
};

export type WeeklyBriefPayload = {
  mosaic_brand: string;
  generated_at: string;
  brief: string;
  report?: {
    title: string;
    generated_at: string;
    overview: DashboardOverview;
    benchmark_highlights?: {
      highest_longevity_competitor?: { competitor?: string; longevity_ratio?: number };
      highest_experimentation_competitor?: { competitor?: string; experimentation_rate?: number };
      largest_theme_shift?: { theme?: string; deviation?: number; direction?: string };
    };
    shift_alerts?: Array<{
      theme: string;
      current_percentage: number;
      baseline_percentage: number;
      deviation: number;
      direction: string;
      severity?: "critical" | "watch";
    }>;
    opportunities?: Array<{
      type: string;
      name: string;
      usage_percentage: number;
      insight?: string;
      action?: string;
    }>;
    priority_actions?: string[];
    watchlist?: string[];
    narrative?: string;
  };
};

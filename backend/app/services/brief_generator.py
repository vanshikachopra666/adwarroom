from __future__ import annotations

import re
from datetime import datetime

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import settings


class WeeklyBriefGenerator:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(2))
    def generate_brief(self, mosaic_brand: str, facts_payload: dict) -> str:
        if not self.client:
            return self._fallback_narrative(mosaic_brand, facts_payload)
        prompt = f"""
You are writing a formal, board-ready competitive intelligence summary.
Write 320-420 words for brand: {mosaic_brand}.
Use exact names and metrics from facts.
Style: sharp, specific, executive, no generic filler.
Must include:
- one paragraph on what changed this week
- one paragraph on what competitors are scaling
- one paragraph on risks/opportunity whitespace
- one paragraph with explicit actions and expected impact
Facts:
{facts_payload}
""".strip()
        try:
            completion = self.client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You produce precise competitive-intelligence briefs."},
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content or ""
            if not self._has_enough_numbers(content):
                raise ValueError("insufficient quantitative detail")
            return content
        except Exception:
            return self._fallback_narrative(mosaic_brand, facts_payload)

    def generate_report(self, mosaic_brand: str, facts_payload: dict) -> dict:
        overview = facts_payload.get("overview", {})
        top_l = facts_payload.get("highest_longevity_competitor", {})
        top_e = facts_payload.get("highest_experimentation_competitor", {})
        shifts = facts_payload.get("shift_alerts", [])[:5]
        opportunities = facts_payload.get("opportunity_gaps", [])[:5]
        longevity_board = facts_payload.get("longevity_leaderboard", [])[:5]
        experimentation_board = facts_payload.get("experimentation_leaderboard", [])[:5]
        top_shift = facts_payload.get("largest_theme_shift", {}) or {}

        actions = [
            (
                "Increase net-new creative velocity by 20-30% this week, with at least 2 assets in the lowest-competition gap theme."
                if opportunities
                else "Increase net-new creative velocity by 15% this week to improve learning speed."
            ),
            (
                f"Clone and adapt the winning pattern from {top_l.get('competitor', 'the longevity leader')} into 2 fresh hooks to extend ad life without fatigue."
            ),
            (
                f"Allocate at least 40% of this week’s output to video-style executions (current benchmark: {overview.get('video_percentage', 0)}%)."
            ),
            (
                "Set an explicit kill/scale framework: pause creatives below benchmark after 3 days; scale top quartile performers by 25-40% budget."
            ),
        ]

        watchlist = [
            "Any message-theme movement above 8 points versus the 4-week baseline.",
            "Longevity ratio shifts above 10 points for top competitors.",
            "Experimentation-rate jumps above 12% indicating aggressive testing cycles.",
        ]

        report = {
            "title": f"Adalyse Weekly Competitive Brief - {mosaic_brand.title()}",
            "generated_at": datetime.utcnow().isoformat(),
            "overview": {
                "total_competitors": overview.get("total_competitors", 0),
                "total_active_ads": overview.get("total_active_ads", 0),
                "video_percentage": overview.get("video_percentage", 0),
                "ugc_percentage": overview.get("ugc_percentage", 0),
                "avg_ad_age": overview.get("avg_ad_age", 0),
                "highest_longevity_brand": overview.get("highest_longevity_brand", "N/A"),
            },
            "benchmark_highlights": {
                "highest_longevity_competitor": top_l,
                "highest_experimentation_competitor": top_e,
                "largest_theme_shift": top_shift,
            },
            "leaderboards": {
                "longevity": longevity_board,
                "experimentation": experimentation_board,
            },
            "shift_alerts": shifts,
            "opportunities": opportunities,
            "priority_actions": actions,
            "watchlist": watchlist,
            "narrative": self.generate_brief(mosaic_brand, facts_payload),
        }
        return report

    @staticmethod
    def _has_enough_numbers(text: str) -> bool:
        return len(re.findall(r"\d+%|\d+(?:\.\d+)?", text)) >= 8

    @staticmethod
    def _fallback_narrative(mosaic_brand: str, facts_payload: dict) -> str:
        overview = facts_payload.get("overview", {})
        top_l = facts_payload.get("highest_longevity_competitor", {})
        top_e = facts_payload.get("highest_experimentation_competitor", {})
        shifts = facts_payload.get("shift_alerts", [])
        top_shift = shifts[0] if shifts else (facts_payload.get("largest_theme_shift", {}) or {})
        opportunities = facts_payload.get("opportunity_gaps", [])[:3]
        opp_text = ", ".join(f"{o.get('name')} ({o.get('usage_percentage', 0)}%)" for o in opportunities) or "no major whitespace gaps"
        return (
            f"{mosaic_brand.title()} is currently tracking {overview.get('total_competitors', 0)} competitors and "
            f"{overview.get('total_active_ads', 0)} active ads, with video share at {overview.get('video_percentage', 0)}% and "
            f"UGC at {overview.get('ugc_percentage', 0)}%. The competitive set is led by {top_l.get('competitor', 'N/A')} on longevity "
            f"({round(float(top_l.get('longevity_ratio', 0)) * 100, 1)}%) and {top_e.get('competitor', 'N/A')} on experimentation "
            f"({round(float(top_e.get('experimentation_rate', 0)) * 100, 1)}%). The largest observed messaging movement is "
            f"{top_shift.get('theme', 'N/A')} with a {top_shift.get('deviation', 0)}-point change versus baseline. "
            f"Current whitespace opportunities include {opp_text}. Recommended focus for the next 7 days: lift creative velocity, "
            f"expand tests in underused themes, and apply strict kill/scale controls to improve efficiency and learning depth."
        )

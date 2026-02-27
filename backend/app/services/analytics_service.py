from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ad import Ad
from app.models.ai_classification import AIClassification
from app.models.competitor import Competitor
from app.models.weekly_metric import WeeklyMetric


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _week_start(self, dt: date | None = None) -> date:
        base = dt or datetime.utcnow().date()
        return base - timedelta(days=base.weekday())

    def recompute_weekly_metrics(self, week_start: date | None = None) -> int:
        week_start = week_start or self._week_start()
        prev_14 = week_start - timedelta(days=14)

        competitors = self.db.execute(select(Competitor)).scalars().all()
        upserts = 0
        for comp in competitors:
            total_active_ads = self.db.execute(
                select(func.count(Ad.id)).where(Ad.competitor_id == comp.id, Ad.is_active.is_(True))
            ).scalar_one()

            new_ads_count = self.db.execute(
                select(func.count(Ad.id)).where(
                    Ad.competitor_id == comp.id,
                    Ad.start_date.is_not(None),
                    Ad.start_date >= prev_14,
                )
            ).scalar_one()

            long_running_ads_count = self.db.execute(
                select(func.count(Ad.id)).where(
                    Ad.competitor_id == comp.id,
                    Ad.is_active.is_(True),
                    Ad.start_date.is_not(None),
                    Ad.start_date <= (week_start - timedelta(days=60)),
                )
            ).scalar_one()

            rows = self.db.execute(
                select(Ad.media_type, AIClassification.creative_format, AIClassification.message_theme)
                .join(AIClassification, AIClassification.ad_id == Ad.id)
                .where(Ad.competitor_id == comp.id)
            ).all()

            total = len(rows) if rows else 1
            ugc_count = sum(1 for _, creative, _ in rows if creative == "UGC")
            video_count = sum(1 for media, _, _ in rows if media == "video")
            authority_count = sum(1 for _, _, theme in rows if theme == "Authority")
            discount_count = sum(1 for _, _, theme in rows if theme == "Discount push")

            metric = self.db.execute(
                select(WeeklyMetric).where(
                    WeeklyMetric.week_start == week_start,
                    WeeklyMetric.competitor_id == comp.id,
                )
            ).scalar_one_or_none()
            if not metric:
                metric = WeeklyMetric(week_start=week_start, competitor_id=comp.id)
                self.db.add(metric)

            metric.total_active_ads = int(total_active_ads or 0)
            metric.new_ads_count = int(new_ads_count or 0)
            metric.long_running_ads_count = int(long_running_ads_count or 0)
            metric.ugc_percentage = round(100 * ugc_count / total, 2)
            metric.video_percentage = round(100 * video_count / total, 2)
            metric.authority_theme_percentage = round(100 * authority_count / total, 2)
            metric.discount_theme_percentage = round(100 * discount_count / total, 2)
            upserts += 1

        self.db.commit()
        return upserts

    def messaging_shift_alerts(self, mosaic_brand: str, week_start: date | None = None) -> list[dict]:
        week_start = week_start or self._week_start()
        comp_ids = self.db.execute(
            select(Competitor.id).where(Competitor.mosaic_brand == mosaic_brand)
        ).scalars().all()

        if not comp_ids:
            return []

        current_rows = self.db.execute(
            select(AIClassification.message_theme, func.count(AIClassification.id))
            .join(Ad, Ad.id == AIClassification.ad_id)
            .where(Ad.competitor_id.in_(comp_ids), Ad.scraped_at >= datetime.combine(week_start, datetime.min.time()))
            .group_by(AIClassification.message_theme)
        ).all()

        rolling_start = week_start - timedelta(days=28)
        rolling_rows = self.db.execute(
            select(AIClassification.message_theme, func.count(AIClassification.id))
            .join(Ad, Ad.id == AIClassification.ad_id)
            .where(
                Ad.competitor_id.in_(comp_ids),
                Ad.scraped_at >= datetime.combine(rolling_start, datetime.min.time()),
                Ad.scraped_at < datetime.combine(week_start, datetime.min.time()),
            )
            .group_by(AIClassification.message_theme)
        ).all()

        current_total = sum(c for _, c in current_rows) or 1
        rolling_total = sum(c for _, c in rolling_rows) or 1

        # When there is too little data, percentage deltas are noisy; keep output conservative.
        if current_total < 20 and rolling_total < 40:
            return []

        current_counts = {k: int(v) for k, v in current_rows}
        rolling_counts = {k: int(v) for k, v in rolling_rows}
        current_dist = {k: 100 * v / current_total for k, v in current_rows}
        rolling_dist = {k: 100 * v / rolling_total for k, v in rolling_rows}

        all_themes = set(current_dist) | set(rolling_dist)
        alerts = []
        for theme in all_themes:
            deviation = current_dist.get(theme, 0) - rolling_dist.get(theme, 0)
            magnitude = abs(deviation)
            current_count = current_counts.get(theme, 0)
            baseline_count = rolling_counts.get(theme, 0)

            severity = ""
            if magnitude >= 20 and (current_count >= 3 or baseline_count >= 3):
                severity = "critical"
            elif magnitude >= 8 and (current_count >= 5 or baseline_count >= 5):
                severity = "watch"

            if severity:
                alerts.append(
                    {
                        "theme": theme,
                        "current_percentage": round(current_dist.get(theme, 0), 2),
                        "baseline_percentage": round(rolling_dist.get(theme, 0), 2),
                        "deviation": round(deviation, 2),
                        "direction": "up" if deviation > 0 else "down",
                        "severity": severity,
                        "current_count": current_count,
                        "baseline_count": baseline_count,
                    }
                )
        if not alerts:
            # Fallback: show top movements as watch items so the panel is still informative.
            candidates = []
            for theme in all_themes:
                deviation = current_dist.get(theme, 0) - rolling_dist.get(theme, 0)
                candidates.append((theme, deviation))
            for theme, deviation in sorted(candidates, key=lambda x: abs(x[1]), reverse=True)[:2]:
                alerts.append(
                    {
                        "theme": theme,
                        "current_percentage": round(current_dist.get(theme, 0), 2),
                        "baseline_percentage": round(rolling_dist.get(theme, 0), 2),
                        "deviation": round(deviation, 2),
                        "direction": "up" if deviation > 0 else "down",
                        "severity": "watch",
                        "current_count": current_counts.get(theme, 0),
                        "baseline_count": rolling_counts.get(theme, 0),
                    }
                )

        alerts.sort(key=lambda x: (0 if x.get("severity") == "critical" else 1, -abs(float(x.get("deviation", 0)))))
        return alerts

    def opportunity_gaps(self, mosaic_brand: str) -> list[dict]:
        comp_ids = self.db.execute(
            select(Competitor.id).where(Competitor.mosaic_brand == mosaic_brand)
        ).scalars().all()
        if not comp_ids:
            return []

        rows = self.db.execute(
            select(Ad.competitor_id, AIClassification.message_theme, AIClassification.creative_format, Ad.media_type)
            .join(Ad, Ad.id == AIClassification.ad_id)
            .where(Ad.competitor_id.in_(comp_ids))
        ).all()

        if not rows:
            return []

        theme_counter = Counter(r[1] for r in rows)
        format_counter = Counter(r[2] for r in rows)
        media_counter = Counter(r[3] for r in rows)
        comp_theme_counter: dict[int, Counter] = defaultdict(Counter)
        comp_format_counter: dict[int, Counter] = defaultdict(Counter)
        for comp_id, theme, creative_format, _media in rows:
            comp_theme_counter[int(comp_id)][theme] += 1
            comp_format_counter[int(comp_id)][creative_format] += 1
        total = len(rows)
        comp_name_map = dict(
            self.db.execute(select(Competitor.id, Competitor.name).where(Competitor.id.in_(comp_ids))).all()
        )

        opportunities: list[dict] = []

        def add_opportunity(
            *,
            gap_type: str,
            dimension: str,
            name: str,
            usage_percentage: float,
            insight: str,
            action: str,
            priority: int,
        ) -> None:
            opportunities.append(
                {
                    "type": gap_type,
                    "dimension": dimension,
                    "name": name,
                    "usage_percentage": round(usage_percentage, 2),
                    "insight": insight,
                    "action": action,
                    "priority": priority,
                }
            )

        known_themes = {
            "Authority",
            "Social proof",
            "Problem agitation",
            "Discount push",
            "Subscription",
            "Ingredient science",
            "Transformation",
            "Community storytelling",
        }
        for theme in sorted(known_themes):
            pct = 100 * theme_counter.get(theme, 0) / total
            if pct < 10:
                add_opportunity(
                    gap_type="Theme Whitespace",
                    dimension="message_theme",
                    name=theme,
                    usage_percentage=pct,
                    insight=f"{theme} appears in only {pct:.1f}% of competitor ads, leaving low-clutter messaging space.",
                    action=f"Launch 2 new creatives anchored on {theme} and track CTR/CVR lift against current control.",
                    priority=2 if pct == 0 else 1,
                )

        known_formats = {"UGC", "Studio", "Doctor-backed", "Influencer", "Meme-style", "Product demo"}
        for creative_format in known_formats:
            pct = 100 * format_counter.get(creative_format, 0) / total
            if pct == 0:
                add_opportunity(
                    gap_type="Untapped Creative Format",
                    dimension="creative_format",
                    name=creative_format,
                    usage_percentage=0.0,
                    insight=f"No competitor is running {creative_format} right now.",
                    action=f"Test {creative_format} with one awareness and one conversion variant this sprint.",
                    priority=3,
                )
            elif pct < 6:
                add_opportunity(
                    gap_type="Low-Saturation Creative Format",
                    dimension="creative_format",
                    name=creative_format,
                    usage_percentage=pct,
                    insight=f"{creative_format} is currently used in only {pct:.1f}% of ads, suggesting underexplored supply.",
                    action=f"Increase {creative_format} share to at least 10% and compare CPA against your current dominant format.",
                    priority=1,
                )

        video_pct = 100 * media_counter.get("video", 0) / total
        if video_pct < 25:
            add_opportunity(
                gap_type="Video Deficit Opportunity",
                dimension="media_type",
                name="video",
                usage_percentage=video_pct,
                insight=f"Video makes up only {video_pct:.1f}% of category creatives, despite stronger scroll-stopping potential.",
                action="Convert top 3 static winners into short-form videos and target a 40% video mix over the next cycle.",
                priority=2,
            )

        top_formats = sorted(format_counter.values(), reverse=True)[:3]
        top_three_share = (sum(top_formats) / total) * 100
        if top_three_share > 80:
            dominant = [k for k, _ in format_counter.most_common(3)]
            add_opportunity(
                gap_type="Creative Concentration Risk",
                dimension="portfolio_mix",
                name=", ".join(dominant),
                usage_percentage=top_three_share,
                insight=f"Top 3 formats account for {top_three_share:.1f}% of category output, signaling low experimentation breadth.",
                action="Allocate 20% of weekly creative volume to non-dominant formats to reduce fatigue risk.",
                priority=2,
            )

        latest_week = self.db.execute(
            select(func.max(WeeklyMetric.week_start)).where(WeeklyMetric.competitor_id.in_(comp_ids))
        ).scalar_one_or_none()
        if latest_week:
            metrics = self.db.execute(
                select(WeeklyMetric).where(
                    WeeklyMetric.week_start == latest_week,
                    WeeklyMetric.competitor_id.in_(comp_ids),
                )
            ).scalars().all()
            if metrics:
                avg_exp = sum((m.new_ads_count / (m.total_active_ads or 1)) for m in metrics) / len(metrics)
                if avg_exp < 0.15:
                    add_opportunity(
                        gap_type="Experimentation Lag",
                        dimension="cadence",
                        name="New creative velocity",
                        usage_percentage=avg_exp * 100,
                        insight=f"Category experimentation is low at {(avg_exp * 100):.1f}% new-ad velocity, which can slow learning cycles.",
                        action="Raise weekly new-ad introductions by 25% to improve signal discovery and reduce saturation dependence.",
                        priority=1,
                    )

                top_longevity = max(
                    metrics,
                    key=lambda m: (m.long_running_ads_count / (m.total_active_ads or 1)),
                    default=None,
                )
                if top_longevity and comp_theme_counter.get(top_longevity.competitor_id):
                    leader_comp = comp_name_map.get(top_longevity.competitor_id, "Leader")
                    leader_theme, leader_theme_count = comp_theme_counter[top_longevity.competitor_id].most_common(1)[0]
                    leader_theme_pct = 100 * theme_counter.get(leader_theme, 0) / total
                    leader_internal_pct = 100 * leader_theme_count / sum(comp_theme_counter[top_longevity.competitor_id].values())
                    if leader_theme_pct < 20:
                        add_opportunity(
                            gap_type="Leader Playbook Gap",
                            dimension="message_theme",
                            name=leader_theme,
                            usage_percentage=leader_theme_pct,
                            insight=f"{leader_comp} leans heavily on {leader_theme} ({leader_internal_pct:.1f}% of its creatives) while the category uses it only {leader_theme_pct:.1f}%.",
                            action=f"Reverse-engineer {leader_comp}'s top {leader_theme} ad and launch 2 differentiated variants within 7 days.",
                            priority=2,
                        )

                top_experimenter = max(
                    metrics,
                    key=lambda m: (m.new_ads_count / (m.total_active_ads or 1)),
                    default=None,
                )
                if top_experimenter and comp_format_counter.get(top_experimenter.competitor_id):
                    exp_comp = comp_name_map.get(top_experimenter.competitor_id, "Top tester")
                    exp_format, exp_format_count = comp_format_counter[top_experimenter.competitor_id].most_common(1)[0]
                    exp_format_pct = 100 * format_counter.get(exp_format, 0) / total
                    exp_internal_pct = 100 * exp_format_count / sum(comp_format_counter[top_experimenter.competitor_id].values())
                    if exp_format_pct < 18:
                        add_opportunity(
                            gap_type="Fast-Tester Blind Spot",
                            dimension="creative_format",
                            name=exp_format,
                            usage_percentage=exp_format_pct,
                            insight=f"{exp_comp} is testing {exp_format} aggressively ({exp_internal_pct:.1f}% of its inventory) while category adoption is just {exp_format_pct:.1f}%.",
                            action=f"Prioritize 3 new {exp_format} concepts this week to close exploration gap with {exp_comp}.",
                            priority=2,
                        )

        opportunities.sort(key=lambda o: (-int(o.get("priority", 0)), float(o.get("usage_percentage", 0))))
        return opportunities[:8]

    def dashboard_payload(
        self,
        mosaic_brand: str | None = None,
        competitor_name: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        creative_format: str | None = None,
        message_theme: str | None = None,
        is_active: bool | None = None,
    ) -> dict:
        comp_query = select(Competitor)
        if mosaic_brand:
            comp_query = comp_query.where(Competitor.mosaic_brand == mosaic_brand)
        if competitor_name:
            comp_query = comp_query.where(Competitor.name == competitor_name)
        competitors = self.db.execute(comp_query).scalars().all()
        comp_ids = [c.id for c in competitors]

        if not comp_ids:
            return {
                "overview": {},
                "format_trend": [],
                "theme_trend": [],
                "longevity": [],
                "experimentation": [],
                "shift_alerts": [],
                "opportunities": [],
            }

        latest_week = self.db.execute(select(func.max(WeeklyMetric.week_start))).scalar_one_or_none()
        metrics = []
        if latest_week:
            metrics = self.db.execute(
                select(WeeklyMetric).where(
                    WeeklyMetric.week_start == latest_week,
                    WeeklyMetric.competitor_id.in_(comp_ids),
                )
            ).scalars().all()

        total_active_ads = sum(m.total_active_ads for m in metrics)
        highest_longevity = max(
            metrics,
            key=lambda m: (m.long_running_ads_count / m.total_active_ads) if m.total_active_ads else 0,
            default=None,
        )
        comp_map = {c.id: c.name for c in competitors}

        ads_query = (
            select(Ad.id, Ad.start_date, Ad.media_type, AIClassification.creative_format, AIClassification.message_theme)
            .join(AIClassification, AIClassification.ad_id == Ad.id)
            .where(Ad.competitor_id.in_(comp_ids))
        )
        if is_active is not None:
            ads_query = ads_query.where(Ad.is_active.is_(is_active))
        if start_date:
            ads_query = ads_query.where(Ad.scraped_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            ads_query = ads_query.where(Ad.scraped_at <= datetime.combine(end_date, datetime.max.time()))
        if creative_format:
            ads_query = ads_query.where(AIClassification.creative_format == creative_format)
        if message_theme:
            ads_query = ads_query.where(AIClassification.message_theme == message_theme)

        latest_ads = self.db.execute(ads_query).all()

        avg_ad_age = 0.0
        if latest_ads:
            ages = [
                (datetime.utcnow().date() - a[1]).days
                for a in latest_ads
                if a[1] is not None
            ]
            avg_ad_age = round(sum(ages) / len(ages), 2) if ages else 0.0

        video_pct = round(100 * sum(1 for a in latest_ads if a[2] == "video") / (len(latest_ads) or 1), 2)
        ugc_pct = round(100 * sum(1 for a in latest_ads if a[3] == "UGC") / (len(latest_ads) or 1), 2)

        by_week_format = defaultdict(lambda: defaultdict(int))
        by_week_theme = defaultdict(lambda: defaultdict(int))
        trend_query = (
            select(Ad.scraped_at, Ad.media_type, AIClassification.message_theme)
            .join(AIClassification, AIClassification.ad_id == Ad.id)
            .where(Ad.competitor_id.in_(comp_ids))
        )
        if start_date:
            trend_query = trend_query.where(Ad.scraped_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            trend_query = trend_query.where(Ad.scraped_at <= datetime.combine(end_date, datetime.max.time()))
        if creative_format:
            trend_query = trend_query.where(AIClassification.creative_format == creative_format)
        if message_theme:
            trend_query = trend_query.where(AIClassification.message_theme == message_theme)
        if is_active is not None:
            trend_query = trend_query.where(Ad.is_active.is_(is_active))

        for scraped_at, media_type, theme in self.db.execute(trend_query):
            week = (scraped_at.date() - timedelta(days=scraped_at.date().weekday())).isoformat()
            by_week_format[week][media_type] += 1
            by_week_theme[week][theme] += 1

        format_trend = [
            {
                "week": week,
                "video": values.get("video", 0),
                "image": values.get("image", 0),
                "carousel": values.get("carousel", 0),
            }
            for week, values in sorted(by_week_format.items())
        ]

        theme_trend = []
        for week, values in sorted(by_week_theme.items()):
            item = {"week": week}
            item.update(values)
            theme_trend.append(item)

        longevity = [
            {
                "competitor": comp_map.get(m.competitor_id, str(m.competitor_id)),
                "long_running_ads": m.long_running_ads_count,
                "total_active_ads": m.total_active_ads,
                "longevity_ratio": round(m.long_running_ads_count / (m.total_active_ads or 1), 4),
            }
            for m in metrics
        ]

        experimentation = [
            {
                "competitor": comp_map.get(m.competitor_id, str(m.competitor_id)),
                "new_ads_count": m.new_ads_count,
                "total_active_ads": m.total_active_ads,
                "experimentation_rate": round(m.new_ads_count / (m.total_active_ads or 1), 4),
            }
            for m in metrics
        ]

        shift_alerts = self.messaging_shift_alerts(mosaic_brand) if mosaic_brand else []
        opportunities = self.opportunity_gaps(mosaic_brand) if mosaic_brand else []

        return {
            "overview": {
                "total_competitors": len(competitors),
                "total_active_ads": total_active_ads,
                "video_percentage": video_pct,
                "ugc_percentage": ugc_pct,
                "avg_ad_age": avg_ad_age,
                "highest_longevity_brand": comp_map.get(highest_longevity.competitor_id, "N/A") if highest_longevity else "N/A",
            },
            "format_trend": format_trend,
            "theme_trend": theme_trend,
            "longevity": sorted(longevity, key=lambda x: x["longevity_ratio"], reverse=True),
            "experimentation": sorted(experimentation, key=lambda x: x["experimentation_rate"], reverse=True),
            "shift_alerts": shift_alerts,
            "opportunities": opportunities,
        }

    def summary_facts_for_brief(self, mosaic_brand: str) -> dict:
        payload = self.dashboard_payload(mosaic_brand)
        longevity = payload["longevity"]
        experimentation = payload["experimentation"]

        top_longevity = longevity[0] if longevity else {}
        top_experimentation = experimentation[0] if experimentation else {}
        top_shift = payload["shift_alerts"][0] if payload["shift_alerts"] else {}

        return {
            "overview": payload["overview"],
            "top_format_shift": top_shift,
            "largest_theme_shift": top_shift,
            "highest_longevity_competitor": top_longevity,
            "highest_experimentation_competitor": top_experimentation,
            "longevity_leaderboard": longevity[:5],
            "experimentation_leaderboard": experimentation[:5],
            "shift_alerts": payload.get("shift_alerts", []),
            "opportunity_gaps": payload["opportunities"],
        }

    def live_actionable_insights(
        self,
        mosaic_brand: str | None = None,
        competitor_name: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        creative_format: str | None = None,
        message_theme: str | None = None,
        is_active: bool | None = None,
    ) -> list[str]:
        payload = self.dashboard_payload(
            mosaic_brand=mosaic_brand,
            competitor_name=competitor_name,
            start_date=start_date,
            end_date=end_date,
            creative_format=creative_format,
            message_theme=message_theme,
            is_active=is_active,
        )
        overview = payload.get("overview") or {}
        insights: list[str] = []

        total_active = int(overview.get("total_active_ads", 0) or 0)
        if total_active == 0:
            return [
                "No active ads are available for this filter set, so run ingestion now and launch 3 fresh creatives this week to establish a measurable baseline."
            ]

        top_longevity = (payload.get("longevity") or [{}])[0]
        if top_longevity and top_longevity.get("competitor"):
            insights.append(
                f"{top_longevity['competitor']} is retaining winners with a {round(float(top_longevity['longevity_ratio']) * 100, 1)}% longevity ratio, so protect budget by cloning your top 2 converting creatives into at least 2 adjacent hooks this week."
            )

        top_experimentation = (payload.get("experimentation") or [{}])[0]
        if top_experimentation and top_experimentation.get("competitor"):
            insights.append(
                f"{top_experimentation['competitor']} is testing fastest at {round(float(top_experimentation['experimentation_rate']) * 100, 1)}% experimentation, so match pace by shipping at least {max(3, int(top_experimentation.get('new_ads_count', 0) or 0))} net-new ads in the next 7 days."
            )

        if overview.get("video_percentage", 0) < 40:
            insights.append(
                f"Video share is only {overview.get('video_percentage', 0)}%, so increase video output to at least 40% of active creatives by converting your top 3 static winners into short UGC-style cuts."
            )

        shift_alerts = payload.get("shift_alerts") or []
        if shift_alerts:
            top_shift = max(shift_alerts, key=lambda x: abs(float(x.get("deviation", 0))))
            direction = "up" if top_shift.get("direction") == "up" else "down"
            action = "scale two new variations around this theme" if direction == "up" else "reduce spend and rotate to adjacent themes"
            insights.append(
                f"{top_shift['theme']} shifted {abs(float(top_shift['deviation'])):.1f} points versus baseline, so {action} in the next campaign refresh."
            )

        opportunities = payload.get("opportunities") or []
        if opportunities:
            top_gap = opportunities[0]
            gap_name = top_gap.get("name", "Gap area")
            gap_type = top_gap.get("type", "Opportunity")
            action = top_gap.get("action", "run a focused test in this lane this week")
            insights.append(
                f"{gap_type} detected in {gap_name} at {top_gap.get('usage_percentage', 0)}% usage, so {action[0].lower() + action[1:] if action else 'run a focused test this week'}"
            )

        return insights[:5]

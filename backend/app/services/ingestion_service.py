from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ad import Ad
from app.models.ai_classification import AIClassification
from app.models.competitor import Competitor
from app.services.ai_classifier import AIClassifier
from app.services.meta_client import MetaAdLibraryClient
from app.services.seed_data import SUBBRAND_FILTERS


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.meta = MetaAdLibraryClient()
        self.ai = AIClassifier()

    def ingest_competitor_ads(self, competitor: Competitor, active_status: str = "ALL", ad_type: str = "ALL") -> int:
        snapshot_ts = datetime.utcnow()
        ads = self.meta.fetch_ads(
            page_id=competitor.facebook_page_id,
            active_status=active_status,
            ad_type=ad_type,
        )

        inserted = 0
        for ad in ads:
            if not self._passes_subbrand_filter(competitor.name, ad.ad_text, ad.headline):
                continue

            existing = self.db.execute(
                select(Ad).where(
                    Ad.competitor_id == competitor.id,
                    Ad.ad_id == ad.ad_id,
                    Ad.scraped_at == snapshot_ts,
                )
            ).scalar_one_or_none()
            if existing:
                continue

            db_ad = Ad(
                competitor_id=competitor.id,
                ad_id=ad.ad_id,
                text=ad.ad_text,
                headline=ad.headline,
                cta=ad.call_to_action,
                media_type=ad.media_type,
                start_date=ad.start_date.date() if ad.start_date else None,
                end_date=ad.end_date.date() if ad.end_date else None,
                is_active=ad.is_active,
                platform=ad.publisher_platform,
                scraped_at=snapshot_ts,
                raw_json=ad.raw_json,
            )
            self.db.add(db_ad)
            self.db.flush()

            classification = self.ai.classify_ad(
                ad_text=db_ad.text,
                headline=db_ad.headline,
                cta=db_ad.cta,
                media_type=db_ad.media_type,
            )
            self.db.add(
                AIClassification(
                    ad_id=db_ad.id,
                    creative_format=classification.creative_format,
                    message_theme=classification.message_theme,
                    funnel_stage=classification.funnel_stage,
                    emotional_tone=classification.emotional_tone,
                )
            )
            inserted += 1

        self.db.commit()
        return inserted

    def ingest_by_brand(self, mosaic_brand: str | None = None) -> dict:
        query = select(Competitor)
        if mosaic_brand:
            query = query.where(Competitor.mosaic_brand == mosaic_brand)
        competitors = self.db.execute(query).scalars().all()

        result: dict[str, int] = {}
        errors: dict[str, str] = {}
        for competitor in competitors:
            key = f"{competitor.mosaic_brand}:{competitor.name}"
            try:
                result[key] = self.ingest_competitor_ads(competitor)
            except Exception as exc:
                result[key] = 0
                errors[key] = str(exc)
        return {"counts": result, "errors": errors}

    def ingest_non_api_demo(self, mosaic_brand: str | None = None, weeks: int = 6, ads_per_week: int = 5) -> dict[str, int]:
        query = select(Competitor)
        if mosaic_brand:
            query = query.where(Competitor.mosaic_brand == mosaic_brand)
        competitors = self.db.execute(query).scalars().all()

        creative_formats = ["UGC", "Studio", "Doctor-backed", "Influencer", "Meme-style", "Product demo"]
        message_themes = [
            "Authority",
            "Social proof",
            "Problem agitation",
            "Discount push",
            "Subscription",
            "Ingredient science",
            "Transformation",
            "Community storytelling",
        ]
        funnel_stages = ["Awareness", "Consideration", "Conversion"]
        emotional_tones = ["Fear", "Aspiration", "Urgency", "Trust", "Empowerment"]
        media_types = ["video", "image", "carousel"]

        for comp in competitors:
            demo_ids = self.db.execute(
                select(Ad.id).where(Ad.competitor_id == comp.id, Ad.ad_id.like("DEMO_%"))
            ).scalars().all()
            if demo_ids:
                self.db.execute(delete(AIClassification).where(AIClassification.ad_id.in_(demo_ids)))
                self.db.execute(delete(Ad).where(Ad.id.in_(demo_ids)))

        counts: dict[str, int] = {}
        now = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
        for comp in competitors:
            inserted = 0
            for week_idx in range(weeks):
                scraped_at = now - timedelta(days=7 * week_idx)
                week_start = scraped_at.date() - timedelta(days=scraped_at.weekday())
                for ad_idx in range(ads_per_week):
                    key = f"{comp.id}:{week_idx}:{ad_idx}"
                    h = int(hashlib.sha256(key.encode()).hexdigest(), 16)

                    media_type = media_types[h % len(media_types)]
                    creative = creative_formats[(h // 3) % len(creative_formats)]
                    theme = message_themes[(h // 7) % len(message_themes)]
                    funnel = funnel_stages[(h // 11) % len(funnel_stages)]
                    tone = emotional_tones[(h // 13) % len(emotional_tones)]
                    is_active = ((h // 17) % 10) < 7
                    start_date = week_start - timedelta(days=(h % 65))
                    end_date = None if is_active else (scraped_at.date() + timedelta(days=((h // 19) % 5)))

                    ad_id = f"DEMO_{comp.id}_{week_idx}_{ad_idx}"
                    db_ad = Ad(
                        competitor_id=comp.id,
                        ad_id=ad_id,
                        text=f"{comp.name} {theme} angle creative #{ad_idx + 1}",
                        headline=f"{comp.name} campaign: {theme}",
                        cta="LEARN_MORE" if funnel != "Conversion" else "SHOP_NOW",
                        media_type=media_type,
                        start_date=start_date,
                        end_date=end_date,
                        is_active=is_active,
                        platform="facebook,instagram",
                        scraped_at=scraped_at,
                        raw_json={"source": "non_api_demo", "competitor": comp.name, "theme": theme, "creative": creative},
                    )
                    self.db.add(db_ad)
                    self.db.flush()
                    self.db.add(
                        AIClassification(
                            ad_id=db_ad.id,
                            creative_format=creative,
                            message_theme=theme,
                            funnel_stage=funnel,
                            emotional_tone=tone,
                        )
                    )
                    inserted += 1
            counts[f"{comp.mosaic_brand}:{comp.name}"] = inserted

        self.db.commit()
        return counts

    @staticmethod
    def _passes_subbrand_filter(competitor_name: str, ad_text: str, headline: str) -> bool:
        keywords = SUBBRAND_FILTERS.get(competitor_name)
        if not keywords:
            return True
        haystack = f"{ad_text} {headline}".lower()
        return any(keyword.lower() in haystack for keyword in keywords)

from app.db.session import SessionLocal
from app.services.analytics_service import AnalyticsService
from app.services.brief_generator import WeeklyBriefGenerator
from app.services.ingestion_service import IngestionService


def run_weekly_pipeline() -> None:
    db = SessionLocal()
    try:
        ingestion = IngestionService(db)
        ingestion.ingest_by_brand(None)

        analytics = AnalyticsService(db)
        analytics.recompute_weekly_metrics()
        brief_gen = WeeklyBriefGenerator()
        for brand in ("bebodywise", "manmatters", "littlejoys"):
            facts = analytics.summary_facts_for_brief(brand)
            if facts.get("overview"):
                brief_gen.generate_brief(brand, facts)
    finally:
        db.close()


if __name__ == "__main__":
    run_weekly_pipeline()

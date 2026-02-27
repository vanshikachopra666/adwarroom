from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.routes import router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.competitor import Competitor
from app.services.seed_data import COMPETITOR_SEEDS

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing_rows = db.execute(select(Competitor)).scalars().all()
        existing_by_key = {(c.name, c.mosaic_brand): c for c in existing_rows}
        seed_keys = {(item["name"], item["mosaic_brand"]) for item in COMPETITOR_SEEDS}

        for item in COMPETITOR_SEEDS:
            key = (item["name"], item["mosaic_brand"])
            row = existing_by_key.get(key)
            if not row:
                db.add(Competitor(**item))
                continue
            row.mosaic_brand = item["mosaic_brand"]
            row.facebook_page_id = item["facebook_page_id"]
            row.justification = item["justification"]
            row.target_audience = item["target_audience"]
            row.price_tier = item["price_tier"]

        for row in existing_rows:
            if (row.name, row.mosaic_brand) not in seed_keys:
                db.delete(row)
        db.commit()
    finally:
        db.close()

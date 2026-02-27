from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Ad(Base):
    __tablename__ = "ads"
    __table_args__ = (
        UniqueConstraint("competitor_id", "ad_id", "scraped_at", name="uq_competitor_ad_scraped"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False, index=True)
    ad_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    headline: Mapped[str] = mapped_column(Text, default="")
    cta: Mapped[str] = mapped_column(String(128), default="")
    media_type: Mapped[str] = mapped_column(String(64), default="image", index=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(128), default="facebook")
    scraped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    competitor = relationship("Competitor", back_populates="ads")
    ai_classification = relationship("AIClassification", back_populates="ad", uselist=False, cascade="all, delete-orphan")

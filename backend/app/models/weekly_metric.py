from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WeeklyMetric(Base):
    __tablename__ = "weekly_metrics"
    __table_args__ = (UniqueConstraint("week_start", "competitor_id", name="uq_week_competitor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id"), nullable=False, index=True)
    total_active_ads: Mapped[int] = mapped_column(Integer, default=0)
    new_ads_count: Mapped[int] = mapped_column(Integer, default=0)
    long_running_ads_count: Mapped[int] = mapped_column(Integer, default=0)
    ugc_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    video_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    authority_theme_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    discount_theme_percentage: Mapped[float] = mapped_column(Float, default=0.0)

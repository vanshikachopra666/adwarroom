from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mosaic_brand: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    facebook_page_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(String(255), nullable=False)
    price_tier: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    ads = relationship("Ad", back_populates="competitor", cascade="all, delete-orphan")

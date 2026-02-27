from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIClassification(Base):
    __tablename__ = "ai_classifications"
    __table_args__ = (UniqueConstraint("ad_id", name="uq_ai_ad"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id"), nullable=False, index=True)
    creative_format: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message_theme: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    funnel_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    emotional_tone: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    ad = relationship("Ad", back_populates="ai_classification")

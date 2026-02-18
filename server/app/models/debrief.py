from typing import Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Debrief(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "debriefs"

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    clarity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    data_support_score: Mapped[int] = mapped_column(Integer, nullable=False)
    handling_score: Mapped[int] = mapped_column(Integer, nullable=False)
    structure_score: Mapped[int] = mapped_column(Integer, nullable=False)
    exchange_resilience_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    moderator_summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    coaching_items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    report_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    unresolved_challenges: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    exchange_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="debrief")

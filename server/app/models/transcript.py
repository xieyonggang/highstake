from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class TranscriptEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transcript_entries"
    __table_args__ = (UniqueConstraint("session_id", "entry_index"),)

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_index: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str] = mapped_column(String(50), nullable=False)
    speaker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    slide_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_claim: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    session = relationship("Session", back_populates="transcript_entries")

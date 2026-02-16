import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SessionStatus(str, enum.Enum):
    CONFIGURING = "configuring"
    READY = "ready"
    PRESENTING = "presenting"
    Q_AND_A = "q_and_a"
    ENDING = "ending"
    COMPLETE = "complete"
    FAILED = "failed"


class Session(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sessions"

    status: Mapped[str] = mapped_column(
        String(20),
        default=SessionStatus.CONFIGURING.value,
        nullable=False,
    )
    interaction_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    intensity: Mapped[str] = mapped_column(String(20), nullable=False)
    agents: Mapped[list] = mapped_column(JSON, default=lambda: ["skeptic", "analyst", "contrarian"], nullable=False)
    focus_areas: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    deck_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("decks.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(), nullable=True)
    duration_secs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recording_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    deck = relationship("Deck", back_populates="sessions", lazy="selectin")
    transcript_entries = relationship(
        "TranscriptEntry",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TranscriptEntry.entry_index",
    )
    debrief = relationship(
        "Debrief",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )

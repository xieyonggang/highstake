from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Deck(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "decks"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    total_slides: Mapped[int] = mapped_column(Integer, nullable=False)
    manifest: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    slides = relationship(
        "Slide",
        back_populates="deck",
        cascade="all, delete-orphan",
        order_by="Slide.slide_index",
    )
    sessions = relationship("Session", back_populates="deck")


class Slide(Base, UUIDMixin):
    __tablename__ = "slides"
    __table_args__ = (UniqueConstraint("deck_id", "slide_index"),)

    deck_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=False,
    )
    slide_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subtitle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_chart: Mapped[bool] = mapped_column(Boolean, default=False)
    has_table: Mapped[bool] = mapped_column(Boolean, default=False)
    thumbnail_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationships
    deck = relationship("Deck", back_populates="slides")

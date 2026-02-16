"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-16
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Decks table (must be created before sessions due to FK)
    op.create_table(
        "decks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("file_key", sa.String(512), nullable=False),
        sa.Column("total_slides", sa.Integer, nullable=False),
        sa.Column("manifest", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="configuring"),
        sa.Column("interaction_mode", sa.String(20), nullable=False),
        sa.Column("intensity", sa.String(20), nullable=False),
        sa.Column("focus_areas", sa.JSON, nullable=False),
        sa.Column("deck_id", sa.String(36), sa.ForeignKey("decks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_secs", sa.Integer, nullable=True),
        sa.Column("recording_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_sessions_status", "sessions", ["status"])
    op.create_index("idx_sessions_created", "sessions", ["created_at"])

    # Slides table
    op.create_table(
        "slides",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("deck_id", sa.String(36), sa.ForeignKey("decks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slide_index", sa.Integer, nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("subtitle", sa.Text, nullable=True),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("has_chart", sa.Boolean, server_default="0"),
        sa.Column("has_table", sa.Boolean, server_default="0"),
        sa.Column("thumbnail_key", sa.String(512), nullable=True),
        sa.UniqueConstraint("deck_id", "slide_index"),
    )
    op.create_index("idx_slides_deck", "slides", ["deck_id", "slide_index"])

    # Transcript entries table
    op.create_table(
        "transcript_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_index", sa.Integer, nullable=False),
        sa.Column("speaker", sa.String(50), nullable=False),
        sa.Column("speaker_name", sa.String(100), nullable=False),
        sa.Column("agent_role", sa.String(50), nullable=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("start_time", sa.Float, nullable=False),
        sa.Column("end_time", sa.Float, nullable=False),
        sa.Column("slide_index", sa.Integer, nullable=True),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("trigger_claim", sa.Text, nullable=True),
        sa.Column("audio_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("session_id", "entry_index"),
    )
    op.create_index("idx_transcript_session", "transcript_entries", ["session_id", "entry_index"])

    # Debriefs table
    op.create_table(
        "debriefs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("overall_score", sa.Integer, nullable=False),
        sa.Column("clarity_score", sa.Integer, nullable=False),
        sa.Column("confidence_score", sa.Integer, nullable=False),
        sa.Column("data_support_score", sa.Integer, nullable=False),
        sa.Column("handling_score", sa.Integer, nullable=False),
        sa.Column("structure_score", sa.Integer, nullable=False),
        sa.Column("moderator_summary", sa.Text, nullable=False),
        sa.Column("strengths", sa.JSON, nullable=False),
        sa.Column("coaching_items", sa.JSON, nullable=False),
        sa.Column("report_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("debriefs")
    op.drop_table("transcript_entries")
    op.drop_table("slides")
    op.drop_table("sessions")
    op.drop_table("decks")

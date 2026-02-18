"""Add claims_json to decks

Revision ID: 002
Revises: 001
Create Date: 2026-02-18
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("decks", sa.Column("claims_json", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("decks", "claims_json")

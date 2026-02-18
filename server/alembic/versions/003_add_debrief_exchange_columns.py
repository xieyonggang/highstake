"""Add exchange columns to debriefs

Revision ID: 003
Revises: 002
Create Date: 2026-02-18
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("debriefs", sa.Column("exchange_resilience_score", sa.Integer, nullable=True))
    op.add_column("debriefs", sa.Column("unresolved_challenges", sa.JSON, nullable=True))
    op.add_column("debriefs", sa.Column("exchange_data", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("debriefs", "exchange_data")
    op.drop_column("debriefs", "unresolved_challenges")
    op.drop_column("debriefs", "exchange_resilience_score")

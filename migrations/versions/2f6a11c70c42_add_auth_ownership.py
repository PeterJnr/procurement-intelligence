"""add authentication ownership

Revision ID: 2f6a11c70c42
Revises: e61b492cf843
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2f6a11c70c42"
down_revision: Union[str, Sequence[str], None] = "e61b492cf843"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing anonymous data remains unowned and is never returned to signed-in users.
    op.add_column("procurement_analysis_runs", sa.Column("owner_id", sa.String(length=100), nullable=True))
    op.create_index("ix_procurement_analysis_run_owner_created", "procurement_analysis_runs", ["owner_id", "created_at"], unique=False)
    op.add_column("conversations", sa.Column("owner_id", sa.String(length=100), nullable=True))
    op.create_index("ix_conversation_owner_updated", "conversations", ["owner_id", "updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_conversation_owner_updated", table_name="conversations")
    op.drop_column("conversations", "owner_id")
    op.drop_index("ix_procurement_analysis_run_owner_created", table_name="procurement_analysis_runs")
    op.drop_column("procurement_analysis_runs", "owner_id")

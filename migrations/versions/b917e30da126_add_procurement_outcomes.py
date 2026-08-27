"""add procurement outcomes

Revision ID: b917e30da126
Revises: f821d19c734a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b917e30da126"
down_revision: Union[str, Sequence[str], None] = "f821d19c734a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "procurement_outcomes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("final_unit_price", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("selected_supplier", sa.String(length=200), nullable=True),
        sa.Column("outcome_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["procurement_analysis_runs.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "outcome IN ('purchased', 'rejected', 'negotiated')",
            name="ck_procurement_outcome_value",
        ),
        sa.CheckConstraint(
            "final_unit_price IS NULL OR final_unit_price > 0",
            name="ck_procurement_outcome_final_price_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", name="uq_procurement_outcome_analysis"),
    )


def downgrade() -> None:
    op.drop_table("procurement_outcomes")

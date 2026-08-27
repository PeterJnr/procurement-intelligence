"""add procurement analysis runs

Revision ID: f821d19c734a
Revises: c4d18e6a921f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f821d19c734a"
down_revision: Union[str, Sequence[str], None] = "c4d18e6a921f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "procurement_analysis_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("manufacturer", sa.String(length=100), nullable=True),
        sa.Column("product_line", sa.String(length=100), nullable=True),
        sa.Column("model_number", sa.String(length=100), nullable=True),
        sa.Column("condition", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("quoted_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("market_data_status", sa.String(length=20), nullable=False),
        sa.Column("match_level", sa.String(length=20), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("assessment", sa.String(length=30), nullable=False),
        sa.Column("recommended_action", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("request_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("analysis_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_procurement_analysis_run_product_created",
        "procurement_analysis_runs",
        ["manufacturer", "model_number", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_procurement_analysis_run_product_created",
        table_name="procurement_analysis_runs",
    )
    op.drop_table("procurement_analysis_runs")

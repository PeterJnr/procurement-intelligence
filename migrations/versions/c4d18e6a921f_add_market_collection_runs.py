"""add market collection runs

Revision ID: c4d18e6a921f
Revises: a781872ff33b
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d18e6a921f"
down_revision: Union[str, Sequence[str], None] = "a781872ff33b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_collection_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_name", sa.String(length=200), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_count", sa.Integer(), nullable=False),
        sa.Column("ready_count", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "collected_count >= 0 AND ready_count >= 0 AND "
            "created_count >= 0 AND updated_count >= 0 AND skipped_count >= 0",
            name="ck_market_collection_run_counts_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_market_collection_run_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_collection_run_started_at",
        "market_collection_runs",
        ["started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_market_collection_run_started_at",
        table_name="market_collection_runs",
    )
    op.drop_table("market_collection_runs")

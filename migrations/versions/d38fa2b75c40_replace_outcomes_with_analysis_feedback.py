"""replace outcomes with analysis feedback

Revision ID: d38fa2b75c40
Revises: b917e30da126
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d38fa2b75c40"
down_revision: Union[str, Sequence[str], None] = "b917e30da126"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("procurement_outcomes")
    op.create_table(
        "analysis_feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("accuracy_score", sa.Integer(), nullable=False),
        sa.Column("product_match_correct", sa.Boolean(), nullable=False),
        sa.Column("evidence_helpful", sa.Boolean(), nullable=False),
        sa.Column("corrected_fair_price", sa.Numeric(18, 2), nullable=True),
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
        sa.CheckConstraint(
            "accuracy_score >= 1 AND accuracy_score <= 5",
            name="ck_analysis_feedback_accuracy_range",
        ),
        sa.CheckConstraint(
            "corrected_fair_price IS NULL OR corrected_fair_price > 0",
            name="ck_analysis_feedback_corrected_price_positive",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["procurement_analysis_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", name="uq_analysis_feedback_analysis"),
    )


def downgrade() -> None:
    op.drop_table("analysis_feedback")
    op.create_table(
        "procurement_outcomes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("final_unit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("selected_supplier", sa.String(length=200), nullable=True),
        sa.Column("outcome_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["procurement_analysis_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id", name="uq_procurement_outcome_analysis"),
    )

"""add conversations and messages

Revision ID: e61b492cf843
Revises: d38fa2b75c40
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e61b492cf843"
down_revision: Union[str, Sequence[str], None] = "d38fa2b75c40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("analysis_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
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
            "status IN ('active', 'archived')",
            name="ck_conversation_status",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["procurement_analysis_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_analysis_updated",
        "conversations",
        ["analysis_id", "updated_at"],
        unique=False,
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_conversation_message_role",
        ),
        sa.CheckConstraint(
            "intent IS NULL OR intent IN "
            "('greeting', 'general_chat', 'procurement_request', "
            "'clarification', 'analysis_follow_up', 'unsupported')",
            name="ck_conversation_message_intent",
        ),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="ck_conversation_message_sequence_positive",
        ),
        sa.CheckConstraint(
            "char_length(btrim(content)) > 0",
            name="ck_conversation_message_content_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_conversation_message_sequence",
        ),
    )
    op.create_index(
        "ix_conversation_message_conversation_created",
        "conversation_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_message_conversation_created",
        table_name="conversation_messages",
    )
    op.drop_table("conversation_messages")
    op.drop_index(
        "ix_conversation_analysis_updated",
        table_name="conversations",
    )
    op.drop_table("conversations")

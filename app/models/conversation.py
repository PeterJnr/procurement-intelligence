import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Conversation(Base):
    """Durable, isolated chat context optionally linked to one analysis."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_conversation_status",
        ),
        Index("ix_conversation_analysis_updated", "analysis_id", "updated_at"),
        Index("ix_conversation_owner_updated", "owner_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_id: Mapped[str | None] = mapped_column(String(100))
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("procurement_analysis_runs.id", ondelete="SET NULL"),
    )
    title: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

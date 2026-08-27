import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalysisFeedback(Base):
    """Human quality signal attached to one procurement analysis."""

    __tablename__ = "analysis_feedback"
    __table_args__ = (
        UniqueConstraint("analysis_id", name="uq_analysis_feedback_analysis"),
        CheckConstraint(
            "accuracy_score >= 1 AND accuracy_score <= 5",
            name="ck_analysis_feedback_accuracy_range",
        ),
        CheckConstraint(
            "corrected_fair_price IS NULL OR corrected_fair_price > 0",
            name="ck_analysis_feedback_corrected_price_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("procurement_analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    accuracy_score: Mapped[int] = mapped_column(Integer, nullable=False)
    product_match_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence_helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    corrected_fair_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


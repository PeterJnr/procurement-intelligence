import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AnalysisFeedbackUpsert(BaseModel):
    accuracy_score: int = Field(ge=1, le=5)
    product_match_correct: bool
    evidence_helpful: bool
    corrected_fair_price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=18,
        decimal_places=2,
    )
    notes: str | None = Field(default=None, max_length=1000)


class AnalysisFeedbackResponse(AnalysisFeedbackUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


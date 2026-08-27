from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class FeedbackPriceCorrectionMetric(BaseModel):
    currency: str
    correction_count: int
    average_price_difference: Decimal
    average_percentage_difference: Decimal


class FeedbackMeasurementSummary(BaseModel):
    measurement_status: Literal["insufficient_feedback", "sufficient_feedback"]
    minimum_feedback_required: int
    feedback_count: int
    average_accuracy_score: Decimal | None
    product_match_correct_rate: Decimal | None
    evidence_helpful_rate: Decimal | None
    corrected_fair_price_count: int
    price_corrections: list[FeedbackPriceCorrectionMetric]


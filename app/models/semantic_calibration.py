from typing import Literal

from pydantic import BaseModel


class SemanticCalibrationSummary(BaseModel):
    calibration_status: Literal[
        "insufficient_feedback",
        "insufficient_label_diversity",
        "recommendation_ready",
    ]
    recommended_action: Literal[
        "collect_more_feedback",
        "retain_current_threshold",
        "review_threshold_change",
    ]
    minimum_semantic_feedback_required: int
    semantic_feedback_count: int
    correct_match_count: int
    incorrect_match_count: int
    current_threshold: float
    recommended_threshold: float | None
    estimated_balanced_accuracy: float | None
    explanation: str

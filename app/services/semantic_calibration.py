import os

from app.models.semantic_calibration import SemanticCalibrationSummary


MINIMUM_SEMANTIC_FEEDBACK = 10
MINIMUM_PER_LABEL = 2


def _semantic_score(analysis_run) -> float | None:
    snapshot = analysis_run.analysis_snapshot
    if snapshot.get("match_level") != "semantic":
        return None
    scores = [
        float(item["semantic_similarity_score"])
        for item in snapshot.get("evidence_observations", [])
        if item.get("retrieval_method") == "semantic"
        and item.get("semantic_similarity_score") is not None
    ]
    return max(scores) if scores else None


def _balanced_accuracy(
    labeled_scores: list[tuple[float, bool]],
    threshold: float,
) -> float:
    positives = [item for item in labeled_scores if item[1]]
    negatives = [item for item in labeled_scores if not item[1]]
    true_positive_rate = sum(score >= threshold for score, _ in positives) / len(
        positives
    )
    true_negative_rate = sum(score < threshold for score, _ in negatives) / len(
        negatives
    )
    return (true_positive_rate + true_negative_rate) / 2


def calibrate_semantic_threshold(records) -> SemanticCalibrationSummary:
    """Recommend a reviewed threshold without modifying runtime configuration."""
    current_threshold = float(os.getenv("PINECONE_MIN_SIMILARITY", "0.65"))
    if not 0 <= current_threshold <= 1:
        raise ValueError("PINECONE_MIN_SIMILARITY must be between 0 and 1")

    labeled_scores = []
    for feedback, analysis_run in records:
        score = _semantic_score(analysis_run)
        if score is not None:
            labeled_scores.append((score, bool(feedback.product_match_correct)))

    feedback_count = len(labeled_scores)
    correct_count = sum(int(label) for _, label in labeled_scores)
    incorrect_count = feedback_count - correct_count
    shared = {
        "minimum_semantic_feedback_required": MINIMUM_SEMANTIC_FEEDBACK,
        "semantic_feedback_count": feedback_count,
        "correct_match_count": correct_count,
        "incorrect_match_count": incorrect_count,
        "current_threshold": current_threshold,
    }

    if feedback_count < MINIMUM_SEMANTIC_FEEDBACK:
        return SemanticCalibrationSummary(
            calibration_status="insufficient_feedback",
            recommended_action="collect_more_feedback",
            recommended_threshold=None,
            estimated_balanced_accuracy=None,
            explanation=(
                "More reviewed semantic analyses are required before threshold "
                "calibration is reliable."
            ),
            **shared,
        )

    if correct_count < MINIMUM_PER_LABEL or incorrect_count < MINIMUM_PER_LABEL:
        return SemanticCalibrationSummary(
            calibration_status="insufficient_label_diversity",
            recommended_action="collect_more_feedback",
            recommended_threshold=None,
            estimated_balanced_accuracy=None,
            explanation=(
                "At least two correct and two incorrect semantic-match labels are "
                "required to compare threshold tradeoffs."
            ),
            **shared,
        )

    candidates = {current_threshold}
    for score, _ in labeled_scores:
        candidates.add(round(score, 3))
        candidates.add(min(1.0, round(score + 0.001, 3)))
    evaluated = [
        (threshold, _balanced_accuracy(labeled_scores, threshold))
        for threshold in candidates
    ]
    recommended_threshold, accuracy = max(
        evaluated,
        key=lambda item: (item[1], -abs(item[0] - current_threshold)),
    )
    recommended_threshold = round(recommended_threshold, 3)
    accuracy = round(accuracy, 3)
    changed = recommended_threshold != round(current_threshold, 3)
    return SemanticCalibrationSummary(
        calibration_status="recommendation_ready",
        recommended_action=(
            "review_threshold_change" if changed else "retain_current_threshold"
        ),
        recommended_threshold=recommended_threshold,
        estimated_balanced_accuracy=accuracy,
        explanation=(
            "The recommendation maximizes balanced accuracy across reviewed correct "
            "and incorrect semantic matches. It must be approved before configuration "
            "is changed."
        ),
        **shared,
    )

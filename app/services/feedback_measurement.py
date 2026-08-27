from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from app.models.feedback_measurement import (
    FeedbackMeasurementSummary,
    FeedbackPriceCorrectionMetric,
)


MINIMUM_FEEDBACK_COUNT = 10
TWO_DECIMAL_PLACES = Decimal("0.01")


def _rounded(value: Decimal) -> Decimal:
    return value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def measure_analysis_feedback(records) -> FeedbackMeasurementSummary:
    """Summarize human feedback without changing any production behavior."""
    feedback_count = len(records)
    if not records:
        return FeedbackMeasurementSummary(
            measurement_status="insufficient_feedback",
            minimum_feedback_required=MINIMUM_FEEDBACK_COUNT,
            feedback_count=0,
            average_accuracy_score=None,
            product_match_correct_rate=None,
            evidence_helpful_rate=None,
            corrected_fair_price_count=0,
            price_corrections=[],
        )

    accuracy_total = sum(
        Decimal(feedback.accuracy_score) for feedback, _ in records
    )
    product_match_count = sum(
        int(feedback.product_match_correct) for feedback, _ in records
    )
    evidence_helpful_count = sum(
        int(feedback.evidence_helpful) for feedback, _ in records
    )

    corrections = defaultdict(list)
    corrected_fair_price_count = 0
    for feedback, analysis_run in records:
        if feedback.corrected_fair_price is None:
            continue
        corrected_fair_price_count += 1
        snapshot = analysis_run.analysis_snapshot
        median_value = snapshot.get("evidence", {}).get("median_unit_price")
        currency = snapshot.get("request", {}).get("currency")
        if median_value is None or currency is None:
            continue
        median_price = Decimal(str(median_value))
        if median_price <= 0:
            continue
        difference = Decimal(feedback.corrected_fair_price) - median_price
        corrections[currency].append(
            (difference, difference / median_price * Decimal("100"))
        )

    correction_metrics = []
    for currency in sorted(corrections):
        values = corrections[currency]
        correction_metrics.append(
            FeedbackPriceCorrectionMetric(
                currency=currency,
                correction_count=len(values),
                average_price_difference=_rounded(
                    sum(value[0] for value in values) / len(values)
                ),
                average_percentage_difference=_rounded(
                    sum(value[1] for value in values) / len(values)
                ),
            )
        )

    denominator = Decimal(feedback_count)
    return FeedbackMeasurementSummary(
        measurement_status=(
            "sufficient_feedback"
            if feedback_count >= MINIMUM_FEEDBACK_COUNT
            else "insufficient_feedback"
        ),
        minimum_feedback_required=MINIMUM_FEEDBACK_COUNT,
        feedback_count=feedback_count,
        average_accuracy_score=_rounded(accuracy_total / denominator),
        product_match_correct_rate=_rounded(
            Decimal(product_match_count) / denominator * Decimal("100")
        ),
        evidence_helpful_rate=_rounded(
            Decimal(evidence_helpful_count) / denominator * Decimal("100")
        ),
        corrected_fair_price_count=corrected_fair_price_count,
        price_corrections=correction_metrics,
    )


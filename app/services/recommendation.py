from app.models.market_price_observation import MarketPriceObservation
from app.models.price_analysis import PriceEvidenceSummary
from app.models.procurement_analysis import (
    ProcurementRecommendation,
    QuoteComparison,
)
from app.models.procurement_request import ProcurementRequest


def build_procurement_recommendation(
    request: ProcurementRequest,
    match_level: str,
    evidence: PriceEvidenceSummary,
    comparison: QuoteComparison,
    observations: list[MarketPriceObservation],
) -> ProcurementRecommendation:
    """Create a cautious deterministic recommendation from available evidence."""
    reason_codes: list[str] = []

    if evidence.evidence_status == "no_data":
        reason_codes.append("no_market_observations")
    elif evidence.evidence_status == "limited":
        reason_codes.append("limited_market_observations")

    if match_level == "none":
        reason_codes.append("no_product_match")
    elif match_level != "exact":
        reason_codes.append("non_exact_product_match")

    quantity_is_represented = any(
        observation.quantity >= request.quantity for observation in observations
    )
    if request.quantity > 1 and not quantity_is_represented:
        reason_codes.append("bulk_quantity_not_represented")

    if (
        evidence.average_source_reliability is not None
        and evidence.average_source_reliability < 0.75
    ):
        reason_codes.append("low_source_reliability")

    blocking_reasons = {
        "no_market_observations",
        "limited_market_observations",
        "no_product_match",
        "non_exact_product_match",
        "bulk_quantity_not_represented",
    }
    if blocking_reasons.intersection(reason_codes):
        return ProcurementRecommendation(
            assessment="undetermined",
            recommended_action="gather_more_evidence",
            confidence="low",
            reason_codes=reason_codes,
        )

    if comparison.position == "above_observed_range":
        assessment = "overpriced"
        recommended_action = "negotiate"
    elif comparison.position == "below_observed_range":
        assessment = "underpriced"
        recommended_action = "verify_quote"
    else:
        assessment = "fair"
        recommended_action = "consider_purchase"

    confidence = (
        "high"
        if evidence.average_source_reliability is not None
        and evidence.average_source_reliability >= 0.75
        else "medium"
    )
    return ProcurementRecommendation(
        assessment=assessment,
        recommended_action=recommended_action,
        confidence=confidence,
        reason_codes=reason_codes,
    )

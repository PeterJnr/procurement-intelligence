import os
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.market_price_observation_schema import MarketPriceObservationFilters
from app.models.procurement_analysis import (
    MarketEvidenceReference,
    ProcurementAnalysisResponse,
    QuoteComparison,
)
from app.models.procurement_request import ProcurementRequest
from app.repositories.market_price_observation import find_comparable_observations
from app.services.laptop_normalization import normalize_laptop_request
from app.services.evidence_matching import explain_evidence_match
from app.services.analysis_explanation import generate_analysis_explanation
from app.services.price_analysis import summarize_price_evidence
from app.services.recommendation import build_procurement_recommendation
from app.services.semantic_retrieval import find_semantic_observations


TWO_DECIMAL_PLACES = Decimal("0.01")
logger = logging.getLogger(__name__)


def _find_best_comparables(session: Session, request: ProcurementRequest, normalized):
    shared = {
        "product_name": normalized.product_name,
        "manufacturer": normalized.manufacturer,
        "product_line": normalized.product_line,
        "model_number": normalized.model_number,
        "condition": normalized.condition,
        "currency": request.currency,
    }

    tiers = []
    if (
        normalized.cpu is not None
        and normalized.ram_gb is not None
        and normalized.storage_capacity_gb is not None
    ):
        tiers.append(
            (
                "exact",
                MarketPriceObservationFilters(
                    **shared,
                    cpu=normalized.cpu,
                    ram_gb=normalized.ram_gb,
                    storage_capacity_gb=normalized.storage_capacity_gb,
                    storage_type=normalized.storage_type,
                ),
            )
        )

    if normalized.ram_gb is not None and normalized.storage_capacity_gb is not None:
        tiers.append(
            (
                "strong",
                MarketPriceObservationFilters(
                    **shared,
                    ram_gb=normalized.ram_gb,
                    storage_capacity_gb=normalized.storage_capacity_gb,
                    storage_type=normalized.storage_type,
                ),
            )
        )

    tiers.append(("broad", MarketPriceObservationFilters(**shared)))

    for match_level, filters in tiers:
        observations = find_comparable_observations(session, filters)
        if observations:
            return match_level, observations, {}

    try:
        observations, similarity_scores = find_semantic_observations(
            session,
            normalized,
            request.currency,
        )
        if observations:
            return "semantic", observations, similarity_scores
    except Exception:
        logger.exception("Semantic market retrieval failed")
    return "none", [], {}


def _compare_quote(
    quoted_price: Decimal,
    currency: str,
    evidence,
) -> QuoteComparison:
    if evidence.median_unit_price is None:
        return QuoteComparison(
            quoted_unit_price=quoted_price,
            currency=currency,
            position="not_available",
            difference_from_median=None,
            percentage_difference_from_median=None,
        )

    difference = quoted_price - evidence.median_unit_price
    percentage = difference / evidence.median_unit_price * Decimal("100")
    if quoted_price < evidence.lowest_unit_price:
        position = "below_observed_range"
    elif quoted_price > evidence.highest_unit_price:
        position = "above_observed_range"
    else:
        position = "within_observed_range"

    return QuoteComparison(
        quoted_unit_price=quoted_price,
        currency=currency,
        position=position,
        difference_from_median=difference.quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        ),
        percentage_difference_from_median=percentage.quantize(
            TWO_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        ),
    )


def _market_data_status(observations) -> str:
    if not observations:
        return "missing"

    max_age_hours = int(os.getenv("MARKET_DATA_MAX_AGE_HOURS", "24"))
    if max_age_hours < 1:
        raise RuntimeError("MARKET_DATA_MAX_AGE_HOURS must be at least 1")
    freshness_cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    latest_seen = max(observation.last_seen_at for observation in observations)
    if latest_seen.tzinfo is None:
        latest_seen = latest_seen.replace(tzinfo=timezone.utc)
    return "fresh" if latest_seen >= freshness_cutoff else "stale"


def analyze_procurement_request(
    session: Session,
    request: ProcurementRequest,
) -> ProcurementAnalysisResponse:
    """Refresh evidence, select the best match tier, and compare the quote."""
    normalized = normalize_laptop_request(request)

    match_level, observations, similarity_scores = _find_best_comparables(
        session, request, normalized
    )
    evidence = summarize_price_evidence(observations)
    quote_comparison = _compare_quote(
        request.quoted_price,
        request.currency,
        evidence,
    )

    evidence_observations = []
    for observation in observations:
        score, matched_fields, different_fields, explanation = (
            explain_evidence_match(normalized, observation)
        )
        similarity_score = similarity_scores.get(observation.id)
        retrieval_method = "semantic" if similarity_score is not None else "deterministic"
        if similarity_score is not None:
            explanation = (
                f"Semantic similarity {similarity_score:.3f}. {explanation}"
            )
        evidence_observations.append(
            MarketEvidenceReference(
                product_name=observation.product_name,
                cpu=observation.cpu,
                ram_gb=observation.ram_gb,
                storage_capacity_gb=observation.storage_capacity_gb,
                storage_type=observation.storage_type,
                condition=observation.condition,
                supplier_name=observation.supplier_name,
                quantity=observation.quantity,
                unit_price=observation.unit_price,
                currency=observation.currency,
                source_name=observation.source_name,
                source_url=observation.source_url,
                observation_date=observation.observation_date,
                source_reliability=observation.source_reliability,
                match_score=score,
                matched_fields=matched_fields,
                different_fields=different_fields,
                match_explanation=explanation,
                retrieval_method=retrieval_method,
                semantic_similarity_score=similarity_score,
            )
        )

    analysis = ProcurementAnalysisResponse(
        request=request,
        normalized_product=normalized,
        market_data_status=_market_data_status(observations),
        match_level=match_level,
        evidence=evidence,
        evidence_observations=evidence_observations,
        quote_comparison=quote_comparison,
        recommendation=build_procurement_recommendation(
            request,
            match_level,
            evidence,
            quote_comparison,
            observations,
        ),
        analysis_explanation="",
        analysis_explanation_status="disabled",
    )
    explanation = generate_analysis_explanation(analysis)
    return analysis.model_copy(
        update={
            "analysis_explanation": explanation.text,
            "analysis_explanation_status": explanation.status,
        }
    )

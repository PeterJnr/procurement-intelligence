import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.normalized_laptop import NormalizedLaptop
from app.models.price_analysis import PriceEvidenceSummary
from app.models.procurement_request import ProcurementRequest


class QuoteComparison(BaseModel):
    quoted_unit_price: Decimal
    currency: str
    position: Literal[
        "below_observed_range",
        "within_observed_range",
        "above_observed_range",
        "not_available",
    ]
    difference_from_median: Decimal | None
    percentage_difference_from_median: Decimal | None


class ProcurementRecommendation(BaseModel):
    assessment: Literal["fair", "overpriced", "underpriced", "undetermined"]
    recommended_action: Literal[
        "consider_purchase",
        "negotiate",
        "verify_quote",
        "gather_more_evidence",
    ]
    confidence: Literal["low", "medium", "high"]
    reason_codes: list[str]


class MarketEvidenceReference(BaseModel):
    product_name: str
    cpu: str
    ram_gb: int
    storage_capacity_gb: int
    storage_type: str
    condition: str
    supplier_name: str
    quantity: int
    unit_price: Decimal
    currency: str
    source_name: str
    source_url: str | None
    observation_date: date
    source_reliability: Decimal
    match_score: int
    matched_fields: list[str]
    different_fields: list[str]
    match_explanation: str
    retrieval_method: Literal["deterministic", "semantic"]
    semantic_similarity_score: float | None


class ProcurementAnalysisResponse(BaseModel):
    analysis_id: uuid.UUID | None = None
    request: ProcurementRequest
    normalized_product: NormalizedLaptop
    market_data_status: Literal["fresh", "stale", "missing"]
    match_level: Literal["exact", "strong", "broad", "semantic", "none"]
    evidence: PriceEvidenceSummary
    evidence_observations: list[MarketEvidenceReference]
    quote_comparison: QuoteComparison
    recommendation: ProcurementRecommendation
    analysis_explanation: str
    analysis_explanation_status: Literal["generated", "fallback", "disabled"]

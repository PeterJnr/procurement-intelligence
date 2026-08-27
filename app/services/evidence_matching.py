from typing import Any

from app.models.normalized_laptop import NormalizedLaptop
from app.models.market_price_observation import MarketPriceObservation


MATCH_WEIGHTS = {
    "manufacturer": 15,
    "product_line": 10,
    "model_number": 25,
    "cpu": 20,
    "ram_gb": 10,
    "storage_capacity_gb": 10,
    "storage_type": 5,
    "condition": 5,
}


def _comparable(value: Any) -> bool:
    return value is not None and value != "unknown"


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, str) and isinstance(right, str):
        return left.strip().casefold() == right.strip().casefold()
    return left == right


def explain_evidence_match(
    requested: NormalizedLaptop,
    observed: MarketPriceObservation,
) -> tuple[int, list[str], list[str], str]:
    """Score and explain an observation using only known request attributes."""
    matched_fields: list[str] = []
    different_fields: list[str] = []
    applicable_weight = 0
    matched_weight = 0

    for field, weight in MATCH_WEIGHTS.items():
        requested_value = getattr(requested, field)
        if not _comparable(requested_value):
            continue
        applicable_weight += weight
        observed_value = getattr(observed, field)
        if _equal(requested_value, observed_value):
            matched_fields.append(field)
            matched_weight += weight
        else:
            different_fields.append(field)

    score = round(matched_weight / applicable_weight * 100) if applicable_weight else 0
    explanation = (
        f"Matched {len(matched_fields)} of "
        f"{len(matched_fields) + len(different_fields)} known request fields"
    )
    if different_fields:
        explanation += f"; differences: {', '.join(different_fields)}."
    else:
        explanation += "; no differences found."
    return score, matched_fields, different_fields, explanation

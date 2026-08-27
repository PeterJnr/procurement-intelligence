from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from app.models.market_price_observation import MarketPriceObservation
from app.models.price_analysis import PriceEvidenceSummary


TWO_DECIMAL_PLACES = Decimal("0.01")
MINIMUM_SUFFICIENT_OBSERVATIONS = 3


def _two_decimal_places(value: Decimal) -> Decimal:
    return value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def summarize_price_evidence(
    observations: list[MarketPriceObservation],
) -> PriceEvidenceSummary:
    """Calculate deterministic statistics for comparable price observations."""
    if not observations:
        return PriceEvidenceSummary(
            evidence_status="no_data",
            observation_count=0,
            currency=None,
            median_unit_price=None,
            lowest_unit_price=None,
            highest_unit_price=None,
            average_source_reliability=None,
        )

    currencies = {observation.currency for observation in observations}
    if len(currencies) != 1:
        raise ValueError("Price observations must use the same currency")

    prices = [Decimal(observation.unit_price) for observation in observations]
    reliability_scores = [
        Decimal(observation.source_reliability) for observation in observations
    ]
    average_reliability = sum(reliability_scores) / len(reliability_scores)

    return PriceEvidenceSummary(
        evidence_status=(
            "sufficient"
            if len(observations) >= MINIMUM_SUFFICIENT_OBSERVATIONS
            else "limited"
        ),
        observation_count=len(observations),
        currency=currencies.pop(),
        median_unit_price=_two_decimal_places(Decimal(median(prices))),
        lowest_unit_price=_two_decimal_places(min(prices)),
        highest_unit_price=_two_decimal_places(max(prices)),
        average_source_reliability=_two_decimal_places(average_reliability),
    )

import unittest
from decimal import Decimal

from app.models.market_price_observation import MarketPriceObservation
from app.models.price_analysis import PriceEvidenceSummary
from app.models.procurement_analysis import QuoteComparison
from app.models.procurement_request import ProcurementRequest
from app.services.recommendation import build_procurement_recommendation


def request(quantity: int = 1) -> ProcurementRequest:
    return ProcurementRequest.model_validate(
        {
            "product": "Dell Latitude 5440",
            "condition": "new",
            "quantity": quantity,
            "quoted_price": "950000",
            "currency": "NGN",
        }
    )


def evidence(status: str = "sufficient") -> PriceEvidenceSummary:
    return PriceEvidenceSummary(
        evidence_status=status,
        observation_count=3,
        currency="NGN",
        median_unit_price=Decimal("850000"),
        lowest_unit_price=Decimal("800000"),
        highest_unit_price=Decimal("900000"),
        average_source_reliability=Decimal("0.80"),
    )


def comparison(position: str) -> QuoteComparison:
    return QuoteComparison(
        quoted_unit_price=Decimal("950000"),
        currency="NGN",
        position=position,
        difference_from_median=Decimal("100000"),
        percentage_difference_from_median=Decimal("11.76"),
    )


def observations(quantity: int = 1) -> list[MarketPriceObservation]:
    return [
        MarketPriceObservation(quantity=quantity),
        MarketPriceObservation(quantity=quantity),
        MarketPriceObservation(quantity=quantity),
    ]


class RecommendationTests(unittest.TestCase):
    def test_exact_sufficient_overpriced_quote_recommends_negotiation(self) -> None:
        result = build_procurement_recommendation(
            request(),
            "exact",
            evidence(),
            comparison("above_observed_range"),
            observations(),
        )

        self.assertEqual(result.assessment, "overpriced")
        self.assertEqual(result.recommended_action, "negotiate")
        self.assertEqual(result.confidence, "high")

    def test_underpriced_quote_requires_verification(self) -> None:
        result = build_procurement_recommendation(
            request(),
            "exact",
            evidence(),
            comparison("below_observed_range"),
            observations(),
        )

        self.assertEqual(result.assessment, "underpriced")
        self.assertEqual(result.recommended_action, "verify_quote")

    def test_bulk_request_without_bulk_evidence_is_undetermined(self) -> None:
        result = build_procurement_recommendation(
            request(quantity=50),
            "exact",
            evidence(),
            comparison("within_observed_range"),
            observations(quantity=1),
        )

        self.assertEqual(result.assessment, "undetermined")
        self.assertEqual(result.recommended_action, "gather_more_evidence")
        self.assertIn("bulk_quantity_not_represented", result.reason_codes)

    def test_non_exact_match_is_not_treated_as_conclusive(self) -> None:
        result = build_procurement_recommendation(
            request(),
            "strong",
            evidence(),
            comparison("within_observed_range"),
            observations(),
        )

        self.assertEqual(result.assessment, "undetermined")
        self.assertIn("non_exact_product_match", result.reason_codes)


if __name__ == "__main__":
    unittest.main()

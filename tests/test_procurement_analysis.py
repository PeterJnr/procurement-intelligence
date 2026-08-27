import unittest
import uuid
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.models.market_price_observation import MarketPriceObservation
from app.models.procurement_request import ProcurementRequest
from app.services.procurement_analysis import analyze_procurement_request


REQUEST = {
    "product": "Dell Latitude 5440",
    "specifications": {
        "cpu": "Intel Core i5",
        "ram": "16GB",
        "storage": "512GB SSD",
    },
    "condition": "new",
    "quantity": 50,
    "quoted_price": "850000.00",
    "currency": "NGN",
}


def observation(
    price: str,
    last_seen_at: datetime | None = None,
) -> MarketPriceObservation:
    return MarketPriceObservation(
        product_name="dell latitude 5440",
        manufacturer="dell",
        product_line="latitude",
        model_number="5440",
        cpu="intel core i5",
        ram_gb=16,
        storage_capacity_gb=512,
        storage_type="ssd",
        condition="new",
        supplier_name="Example Supplier",
        unit_price=Decimal(price),
        source_reliability=Decimal("0.60"),
        currency="NGN",
        quantity=1,
        source_name="Example Market",
        source_url="https://example.com/listing",
        observation_date=date(2026, 8, 26),
        last_seen_at=last_seen_at or datetime.now(timezone.utc),
    )


class ProcurementAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.external_ai = patch.dict(
            os.environ,
            {
                "ENABLE_SEMANTIC_RETRIEVAL": "false",
                "ENABLE_LANGCHAIN_EXPLANATION": "false",
            },
        )
        self.external_ai.start()
        self.addCleanup(self.external_ai.stop)
        self.session = MagicMock(spec=Session)
        self.request = ProcurementRequest.model_validate(REQUEST)
    @patch("app.services.procurement_analysis.find_comparable_observations")
    def test_strong_fallback_is_used_when_exact_match_is_empty(
        self,
        find,
    ) -> None:
        find.side_effect = [[], [observation("800000"), observation("900000")]]

        result = analyze_procurement_request(self.session, self.request)

        self.assertEqual(result.market_data_status, "fresh")
        self.assertEqual(result.match_level, "strong")
        self.assertEqual(result.evidence.median_unit_price, Decimal("850000.00"))
        self.assertEqual(len(result.evidence_observations), 2)
        self.assertEqual(
            result.evidence_observations[0].supplier_name,
            "Example Supplier",
        )
        self.assertEqual(
            result.evidence_observations[0].source_url,
            "https://example.com/listing",
        )
        self.assertEqual(result.evidence_observations[0].match_score, 100)
        self.assertEqual(
            result.evidence_observations[0].retrieval_method,
            "deterministic",
        )
        self.assertIsNone(
            result.evidence_observations[0].semantic_similarity_score
        )
        self.assertEqual(result.evidence_observations[0].different_fields, [])
        self.assertIn(
            "no differences found",
            result.evidence_observations[0].match_explanation,
        )
        self.assertEqual(result.quote_comparison.position, "within_observed_range")
        self.assertEqual(result.quote_comparison.percentage_difference_from_median, 0)
        self.assertEqual(result.recommendation.assessment, "undetermined")
        self.assertEqual(
            result.recommendation.recommended_action,
            "gather_more_evidence",
        )
        self.assertIn("non_exact_product_match", result.recommendation.reason_codes)
        self.assertIn(
            "bulk_quantity_not_represented",
            result.recommendation.reason_codes,
        )

    @patch("app.services.procurement_analysis.find_comparable_observations")
    def test_old_stored_evidence_is_marked_stale(self, find) -> None:
        find.return_value = [
            observation(
                "900000",
                datetime.now(timezone.utc) - timedelta(days=2),
            )
        ]

        result = analyze_procurement_request(self.session, self.request)

        self.assertEqual(result.market_data_status, "stale")
        self.assertEqual(result.match_level, "exact")
        self.assertEqual(result.quote_comparison.position, "below_observed_range")

    @patch("app.services.procurement_analysis.find_comparable_observations")
    def test_specification_difference_is_explained(self, find) -> None:
        different_cpu = observation("900000")
        different_cpu.cpu = "intel core i7"
        find.side_effect = [[], [different_cpu]]

        result = analyze_procurement_request(self.session, self.request)

        reference = result.evidence_observations[0]
        self.assertEqual(result.match_level, "strong")
        self.assertEqual(reference.match_score, 80)
        self.assertIn("cpu", reference.different_fields)
        self.assertNotIn("cpu", reference.matched_fields)
        self.assertIn("differences: cpu", reference.match_explanation)

    @patch("app.services.procurement_analysis.find_comparable_observations")
    def test_no_evidence_returns_no_comparison(self, find) -> None:
        find.return_value = []

        result = analyze_procurement_request(self.session, self.request)

        self.assertEqual(result.match_level, "none")
        self.assertEqual(result.market_data_status, "missing")
        self.assertEqual(result.evidence.evidence_status, "no_data")
        self.assertEqual(result.evidence_observations, [])
        self.assertEqual(result.quote_comparison.position, "not_available")

    @patch("app.services.procurement_analysis.find_semantic_observations")
    @patch("app.services.procurement_analysis.find_comparable_observations")
    def test_semantic_fallback_exposes_similarity_provenance(
        self,
        find,
        semantic_find,
    ) -> None:
        find.return_value = []
        semantic_observation = observation("900000")
        semantic_observation.id = uuid.UUID(
            "11111111-1111-1111-1111-111111111111"
        )
        semantic_find.return_value = (
            [semantic_observation],
            {semantic_observation.id: 0.91},
        )

        with patch.dict(os.environ, {"ENABLE_SEMANTIC_RETRIEVAL": "true"}):
            result = analyze_procurement_request(self.session, self.request)

        reference = result.evidence_observations[0]
        self.assertEqual(result.match_level, "semantic")
        self.assertEqual(reference.retrieval_method, "semantic")
        self.assertEqual(reference.semantic_similarity_score, 0.91)
        self.assertIn("Semantic similarity 0.910", reference.match_explanation)


if __name__ == "__main__":
    unittest.main()

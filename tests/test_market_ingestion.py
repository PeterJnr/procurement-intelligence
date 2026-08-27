import os
import unittest
from unittest.mock import MagicMock, patch

from app.services.jumia_enrichment import enrich_jumia_candidate_from_html
from app.services.listing_extraction import extract_listing_candidate
from app.services.market_ingestion import _sync_vector_if_enabled, candidate_to_observation
from tests.test_jumia_enrichment import PRODUCT_JSON_LD, candidate_title


class MarketIngestionTests(unittest.TestCase):
    def test_ready_candidate_converts_to_observation(self) -> None:
        candidate = extract_listing_candidate(candidate_title())
        candidate = enrich_jumia_candidate_from_html(candidate, PRODUCT_JSON_LD)

        observation = candidate_to_observation(candidate)

        self.assertEqual(observation.product_name, "dell latitude 5440")
        self.assertEqual(observation.supplier_name, "Sharon System")
        self.assertEqual(observation.condition, "new")
        self.assertEqual(observation.quantity, 1)
        self.assertEqual(observation.currency, "NGN")
        self.assertEqual(observation.source_external_id, "123456789")

    def test_incomplete_candidate_cannot_be_stored(self) -> None:
        candidate = extract_listing_candidate(candidate_title())

        with self.assertRaisesRegex(ValueError, "must be ready"):
            candidate_to_observation(candidate)

    def test_enabled_vector_sync_is_invoked(self) -> None:
        observation = MagicMock()
        with (
            patch.dict(os.environ, {"ENABLE_VECTOR_SYNC": "true"}),
            patch(
                "app.services.market_ingestion.sync_market_observation_vector"
            ) as sync,
        ):
            _sync_vector_if_enabled(observation)

        sync.assert_called_once_with(observation)

    def test_vector_failure_does_not_reject_stored_observation(self) -> None:
        observation = MagicMock()
        observation.id = "observation-id"
        with (
            patch.dict(os.environ, {"ENABLE_VECTOR_SYNC": "true"}),
            patch(
                "app.services.market_ingestion.sync_market_observation_vector",
                side_effect=RuntimeError("provider unavailable"),
            ),
            self.assertLogs("app.services.market_ingestion", level="ERROR"),
        ):
            _sync_vector_if_enabled(observation)


if __name__ == "__main__":
    unittest.main()

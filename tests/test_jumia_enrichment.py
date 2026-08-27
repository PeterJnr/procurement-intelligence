import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from urllib.error import URLError

from app.models.collected_market_listing import CollectedMarketListing
from app.services.jumia_enrichment import (
    enrich_jumia_candidate_from_html,
    enrich_jumia_candidates,
    extract_jumia_detail_metadata,
)
from app.services.listing_extraction import extract_listing_candidate


PRODUCT_JSON_LD = """
<script type="application/ld+json">
{
  "@type": "Product",
  "offers": {
    "@type": "Offer",
    "itemCondition": "http://schema.org/NewCondition",
    "seller": {"@type": "Organization", "name": "Sharon System"}
  }
}
</script>
"""


def candidate_title() -> CollectedMarketListing:
    return CollectedMarketListing(
        title=(
            "DELL Latitude 5440 Intel Core i7 16GB RAM 512GB SSD"
        ),
        unit_price=Decimal("1350000"),
        source_url="https://www.jumia.com.ng/example-123456789.html",
        source_external_id="123456789",
        collected_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )


class JumiaEnrichmentTests(unittest.TestCase):
    def test_seller_and_condition_are_extracted_from_json_ld(self) -> None:
        supplier, condition = extract_jumia_detail_metadata(PRODUCT_JSON_LD)

        self.assertEqual(supplier, "Sharon System")
        self.assertEqual(condition, "new")

    def test_complete_candidate_becomes_ready(self) -> None:
        candidate = extract_listing_candidate(candidate_title())

        enriched = enrich_jumia_candidate_from_html(candidate, PRODUCT_JSON_LD)

        self.assertEqual(enriched.supplier_name, "Sharon System")
        self.assertEqual(enriched.condition, "new")
        self.assertEqual(enriched.missing_fields, [])
        self.assertEqual(enriched.validation_status, "ready")

    def test_missing_json_ld_remains_unresolved(self) -> None:
        candidate = extract_listing_candidate(candidate_title())

        enriched = enrich_jumia_candidate_from_html(candidate, "<html></html>")

        self.assertIn("condition", enriched.missing_fields)
        self.assertIn("supplier", enriched.missing_fields)
        self.assertEqual(enriched.validation_status, "needs_enrichment")

    def test_one_unavailable_product_page_does_not_crash_batch(self) -> None:
        candidate = extract_listing_candidate(candidate_title())

        with patch(
            "app.services.jumia_enrichment.enrich_jumia_candidate",
            side_effect=URLError("temporarily unavailable"),
        ):
            enriched = enrich_jumia_candidates([candidate])

        self.assertEqual(enriched, [candidate])
        self.assertEqual(enriched[0].validation_status, "needs_enrichment")


if __name__ == "__main__":
    unittest.main()

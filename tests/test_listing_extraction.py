import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.models.collected_market_listing import CollectedMarketListing
from app.services.listing_extraction import extract_listing_candidate


def listing(title: str) -> CollectedMarketListing:
    return CollectedMarketListing(
        title=title,
        unit_price=Decimal("850000"),
        source_url="https://www.jumia.com.ng/example-123456789.html",
        source_external_id="123456789",
        collected_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )


class ListingExtractionTests(unittest.TestCase):
    def test_explicit_laptop_attributes_are_extracted(self) -> None:
        candidate = extract_listing_candidate(
            listing(
                "DELL Latitude 5440 Intel Core i5 16GB RAM "
                "512GB SSD New"
            )
        )

        self.assertEqual(candidate.manufacturer, "dell")
        self.assertEqual(candidate.product_line, "latitude")
        self.assertEqual(candidate.model_number, "5440")
        self.assertEqual(candidate.cpu, "intel core i5")
        self.assertEqual(candidate.ram_gb, 16)
        self.assertEqual(candidate.storage_capacity_gb, 512)
        self.assertEqual(candidate.storage_type, "ssd")
        self.assertEqual(candidate.condition, "new")
        self.assertEqual(candidate.missing_fields, ["supplier"])
        self.assertEqual(candidate.validation_status, "needs_enrichment")

    def test_tb_storage_and_refurbished_condition_are_normalized(self) -> None:
        candidate = extract_listing_candidate(
            listing(
                "Lenovo ThinkPad T14 Intel Core i7 32GB RAM 1TB SSD Renewed"
            )
        )

        self.assertEqual(candidate.model_number, "t14")
        self.assertEqual(candidate.storage_capacity_gb, 1024)
        self.assertEqual(candidate.condition, "refurbished")

    def test_decorative_symbols_do_not_block_cpu_extraction(self) -> None:
        candidate = extract_listing_candidate(
            listing(
                "DELL Latitude 5440 Intel® Core™ I7 16GB RAM 512GB SSD"
            )
        )

        self.assertEqual(candidate.cpu, "intel core i7")

    def test_absent_information_is_reported_not_guessed(self) -> None:
        candidate = extract_listing_candidate(listing("Dell business laptop"))

        self.assertIsNone(candidate.model_number)
        self.assertIsNone(candidate.cpu)
        self.assertIsNone(candidate.condition)
        self.assertIn("model_number", candidate.missing_fields)
        self.assertIn("condition", candidate.missing_fields)
        self.assertEqual(candidate.validation_status, "needs_enrichment")


if __name__ == "__main__":
    unittest.main()

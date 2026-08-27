import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.services.kara_collector import parse_kara_product


KARA_HTML = """
<script type="application/ld+json">
{
  "@type": "Product",
  "name": "Dell Latitude 5440 laptop intel core i5-1345U",
  "sku": "12032",
  "offers": {
    "priceCurrency": "NGN",
    "price": 1356000,
    "itemCondition": "https://schema.org/NewCondition",
    "seller": {"@type": "Organization", "name": "Kara Nigeria"}
  }
}
</script>
<table>
  <tr><td><strong>RAM</strong></td><td>8GB DDR4</td></tr>
  <tr><td><strong>Storage</strong></td><td>256GB PCIe NVMe M.2 SSD</td></tr>
</table>
"""


class KaraCollectorTests(unittest.TestCase):
    def test_structured_product_becomes_ready_candidate(self) -> None:
        candidate = parse_kara_product(
            KARA_HTML,
            "https://kara.com.ng/dell-latitude-5440",
            datetime(2026, 8, 25, tzinfo=timezone.utc),
        )

        self.assertEqual(candidate.manufacturer, "dell")
        self.assertEqual(candidate.model_number, "5440")
        self.assertEqual(candidate.cpu, "intel core i5-1345u")
        self.assertEqual(candidate.ram_gb, 8)
        self.assertEqual(candidate.storage_capacity_gb, 256)
        self.assertEqual(candidate.storage_type, "ssd")
        self.assertEqual(candidate.condition, "new")
        self.assertEqual(candidate.supplier_name, "Kara Nigeria")
        self.assertEqual(candidate.raw_listing.unit_price, Decimal("1356000"))
        self.assertEqual(candidate.raw_listing.source_external_id, "12032")
        self.assertEqual(candidate.validation_status, "ready")


if __name__ == "__main__":
    unittest.main()

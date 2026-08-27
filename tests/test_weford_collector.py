import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.services.weford_collector import (
    ProductUnavailableError,
    parse_weford_product,
)


WEFORD_HTML = """
<html><body>
<h1>Dell Latitude 5440 (i5, Touchscreen)</h1>
<p>In Stock, Ready to Ship</p>
<p>₦1,300,000</p>
<h2>Specifications</h2>
<div>Processor</div><div>Intel Core i5 (13th Gen)</div>
<div>Memory</div><div>16GB RAM</div>
<div>Storage</div><div>512GB SSD</div>
<div>Operating System</div><div>Windows 11 Pro</div>
<p>Every Dell laptop sold by WeFord Enterprise is 100% brand-new.</p>
</body></html>
"""


class WeFordCollectorTests(unittest.TestCase):
    def test_in_stock_product_becomes_ready_candidate(self) -> None:
        candidate = parse_weford_product(
            WEFORD_HTML,
            "https://www.wefordenterprise.com/shop/dell-latitude-5440-i5-touch",
            datetime(2026, 8, 26, tzinfo=timezone.utc),
        )

        self.assertEqual(candidate.manufacturer, "dell")
        self.assertEqual(candidate.model_number, "5440")
        self.assertEqual(candidate.cpu, "intel core i5")
        self.assertEqual(candidate.ram_gb, 16)
        self.assertEqual(candidate.storage_capacity_gb, 512)
        self.assertEqual(candidate.storage_type, "ssd")
        self.assertEqual(candidate.condition, "new")
        self.assertEqual(candidate.supplier_name, "WeFord Enterprise")
        self.assertEqual(candidate.raw_listing.unit_price, Decimal("1300000"))
        self.assertEqual(candidate.validation_status, "ready")

    def test_out_of_stock_product_is_rejected(self) -> None:
        html = WEFORD_HTML.replace(
            "In Stock, Ready to Ship",
            "Out of Stock",
        )

        with self.assertRaisesRegex(ProductUnavailableError, "not confirmed"):
            parse_weford_product(html, "https://www.wefordenterprise.com/shop/example")


if __name__ == "__main__":
    unittest.main()

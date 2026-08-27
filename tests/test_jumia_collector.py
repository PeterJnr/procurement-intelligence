import unittest
from datetime import datetime, timezone
from decimal import Decimal

from app.services.jumia_collector import parse_jumia_listings


SAMPLE_HTML = """
<article class="prd _fb col c-prd">
  <a class="core" href="/dell-latitude-5440-example-419211020.html">
    <div class="info">
      <h3 class="name">DELL Latitude 5440 Intel Core i5 16GB RAM 512GB SSD</h3>
      <div class="prc">₦ 850,000</div>
    </div>
  </a>
</article>
"""


class JumiaCollectorTests(unittest.TestCase):
    def test_listing_html_is_parsed_deterministically(self) -> None:
        collected_at = datetime(2026, 8, 25, tzinfo=timezone.utc)

        listings = parse_jumia_listings(SAMPLE_HTML, collected_at)

        self.assertEqual(len(listings), 1)
        self.assertEqual(
            listings[0].title,
            "DELL Latitude 5440 Intel Core i5 16GB RAM 512GB SSD",
        )
        self.assertEqual(listings[0].unit_price, Decimal("850000"))
        self.assertEqual(listings[0].currency, "NGN")
        self.assertEqual(
            listings[0].source_url,
            "https://www.jumia.com.ng/dell-latitude-5440-example-419211020.html",
        )
        self.assertEqual(listings[0].source_external_id, "419211020")
        self.assertEqual(listings[0].collected_at, collected_at)

    def test_incomplete_cards_are_ignored(self) -> None:
        self.assertEqual(parse_jumia_listings("<article class='prd'></article>"), [])


if __name__ == "__main__":
    unittest.main()

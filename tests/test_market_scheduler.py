import os
import unittest
from unittest.mock import patch

from app.services.market_scheduler import (
    configured_products,
    create_market_scheduler,
    weford_collection_enabled,
)


class MarketSchedulerTests(unittest.TestCase):
    def test_configured_products_are_parsed(self) -> None:
        with patch.dict(
            os.environ,
            {"MARKET_COLLECTION_PRODUCTS": "Dell Latitude 5440, HP EliteBook 840"},
        ):
            self.assertEqual(
                configured_products(),
                ["Dell Latitude 5440", "HP EliteBook 840"],
            )

    def test_scheduler_has_one_non_overlapping_refresh_job(self) -> None:
        scheduler = create_market_scheduler()
        scheduler.start(paused=True)
        try:
            jobs = scheduler.get_jobs()
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].id, "market-data-refresh")
            self.assertEqual(jobs[0].max_instances, 1)
            self.assertTrue(jobs[0].coalesce)
        finally:
            scheduler.shutdown(wait=False)

    def test_weford_collection_requires_explicit_enablement(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(weford_collection_enabled())
        with patch.dict(os.environ, {"ENABLE_WEFORD_COLLECTION": "true"}):
            self.assertTrue(weford_collection_enabled())


if __name__ == "__main__":
    unittest.main()

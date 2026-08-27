import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi import BackgroundTasks, HTTPException

from app.main import trigger_market_collection
from app.main import app
from app.security import verify_market_admin_key
from app.services import market_scheduler


class MarketAdminTests(unittest.TestCase):
    def test_market_write_and_operations_expose_admin_security(self) -> None:
        paths = app.openapi()["paths"]

        self.assertEqual(
            paths["/market-price-observations"]["post"]["security"],
            [{"APIKeyHeader": []}],
        )
        self.assertEqual(
            paths["/market-collection-runs"]["get"]["security"],
            [{"APIKeyHeader": []}],
        )
        self.assertEqual(
            paths["/market-collection-runs/trigger"]["post"]["security"],
            [{"APIKeyHeader": []}],
        )
        self.assertEqual(
            paths["/procurement-analysis-runs"]["get"]["security"],
            [{"APIKeyHeader": []}],
        )
        self.assertEqual(
            paths["/procurement-analysis-runs/{analysis_id}/feedback"]["put"][
                "security"
            ],
            [{"APIKeyHeader": []}],
        )
        self.assertEqual(
            paths["/procurement-analysis-runs/{analysis_id}/feedback"]["get"][
                "security"
            ],
            [{"APIKeyHeader": []}],
        )
        self.assertEqual(
            paths["/analysis-feedback/summary"]["get"]["security"],
            [{"APIKeyHeader": []}],
        )
        self.assertEqual(
            paths["/market-vectors/backfill"]["post"]["security"],
            [{"APIKeyHeader": []}],
        )
        self.assertEqual(
            paths["/analysis-feedback/semantic-calibration"]["get"]["security"],
            [{"APIKeyHeader": []}],
        )

    def test_market_observation_read_remains_unprotected(self) -> None:
        operation = app.openapi()["paths"]["/market-price-observations"]["get"]

        self.assertNotIn("security", operation)

    def test_missing_configuration_returns_503(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as context:
                verify_market_admin_key("anything")

        self.assertEqual(context.exception.status_code, 503)

    def test_invalid_key_returns_401(self) -> None:
        with patch.dict(os.environ, {"MARKET_ADMIN_API_KEY": "correct-key"}):
            with self.assertRaises(HTTPException) as context:
                verify_market_admin_key("wrong-key")

        self.assertEqual(context.exception.status_code, 401)

    def test_valid_key_is_accepted(self) -> None:
        with patch.dict(os.environ, {"MARKET_ADMIN_API_KEY": "correct-key"}):
            self.assertIsNone(verify_market_admin_key("correct-key"))

    @patch("app.main.queue_market_collection", return_value=True)
    def test_trigger_returns_202_response_body(self, queue) -> None:
        tasks = BackgroundTasks()

        response = trigger_market_collection(tasks)

        queue.assert_called_once_with(tasks)
        self.assertEqual(response.status, "accepted")

    @patch("app.main.queue_market_collection", return_value=False)
    def test_trigger_rejects_overlapping_collection(self, queue) -> None:
        with self.assertRaises(HTTPException) as context:
            trigger_market_collection(BackgroundTasks())

        self.assertEqual(context.exception.status_code, 409)

    def test_scheduler_skips_when_shared_lock_is_held(self) -> None:
        market_scheduler._collection_lock.acquire()
        try:
            with patch("app.services.market_scheduler._collect_market_data") as collect:
                self.assertFalse(market_scheduler.run_market_collection_job())
                collect.assert_not_called()
        finally:
            market_scheduler._collection_lock.release()

    def test_manual_collection_reserves_lock_before_queueing(self) -> None:
        tasks = MagicMock()

        self.assertTrue(market_scheduler.queue_market_collection(tasks))
        try:
            self.assertTrue(market_scheduler._collection_lock.locked())
            tasks.add_task.assert_called_once_with(
                market_scheduler._run_prelocked_market_collection
            )
        finally:
            market_scheduler._collection_lock.release()


if __name__ == "__main__":
    unittest.main()

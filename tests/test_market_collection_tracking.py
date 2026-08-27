import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.models.market_collection_run import MarketCollectionRun
from app.models.market_ingestion import MarketIngestionResult
from app.repositories.market_collection_run import fail_collection_run
from app.services.market_scheduler import _run_tracked_collection


class MarketCollectionTrackingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock(spec=Session)
        self.run = MarketCollectionRun(
            source_name="Jumia Nigeria",
            product_name="Dell Latitude 5440",
            status="running",
        )

    @patch("app.services.market_scheduler.complete_collection_run")
    @patch("app.services.market_scheduler.create_collection_run")
    def test_successful_collection_is_completed(self, create, complete) -> None:
        create.return_value = self.run
        result = MarketIngestionResult(
            collected_count=4,
            ready_count=3,
            created_count=1,
            updated_count=2,
            skipped_count=1,
        )

        _run_tracked_collection(
            self.session,
            "Jumia Nigeria",
            "Dell Latitude 5440",
            lambda: result,
        )

        create.assert_called_once_with(
            self.session, "Jumia Nigeria", "Dell Latitude 5440"
        )
        complete.assert_called_once_with(self.session, self.run, result)

    @patch("app.services.market_scheduler.fail_collection_run")
    @patch("app.services.market_scheduler.create_collection_run")
    def test_failed_collection_is_recorded(self, create, fail) -> None:
        create.return_value = self.run
        error = TimeoutError("upstream timeout with private details")

        _run_tracked_collection(
            self.session,
            "Jumia Nigeria",
            "Dell Latitude 5440",
            MagicMock(side_effect=error),
        )

        self.session.rollback.assert_called_once()
        fail.assert_called_once_with(self.session, self.run, error)

    def test_model_has_status_and_count_constraints(self) -> None:
        constraint_names = {
            constraint.name for constraint in MarketCollectionRun.__table__.constraints
        }

        self.assertIn("ck_market_collection_run_status", constraint_names)
        self.assertIn(
            "ck_market_collection_run_counts_nonnegative", constraint_names
        )

    def test_failure_record_does_not_store_private_error_details(self) -> None:
        error = RuntimeError("secret upstream detail")

        fail_collection_run(self.session, self.run, error)

        self.assertEqual(self.run.status, "failed")
        self.assertEqual(self.run.error_message, "RuntimeError: collection failed")
        self.assertNotIn("secret", self.run.error_message)


if __name__ == "__main__":
    unittest.main()

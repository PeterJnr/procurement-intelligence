import os
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.services.vector_backfill import (
    VectorBackfillNotConfiguredError,
    backfill_market_observation_vectors,
)


VECTOR_ENVIRONMENT = {
    "ENABLE_VECTOR_SYNC": "true",
    "HF_TOKEN": "test-token",
    "HF_EMBEDDING_MODEL": "test-model",
    "PINECONE_API_KEY": "test-key",
    "PINECONE_INDEX_NAME": "test-index",
    "PINECONE_NAMESPACE": "test-namespace",
}


class VectorBackfillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock(spec=Session)

    @patch("app.services.vector_backfill.sync_market_observation_vector")
    @patch("app.services.vector_backfill.list_observations_for_vector_backfill")
    def test_batch_reports_success_failure_and_next_offset(self, list_records, sync):
        observations = [MagicMock(), MagicMock()]
        list_records.return_value = observations
        sync.side_effect = [None, RuntimeError("provider unavailable")]

        with patch.dict(os.environ, VECTOR_ENVIRONMENT):
            result = backfill_market_observation_vectors(
                self.session,
                limit=2,
                offset=4,
            )

        self.assertEqual(result.processed_count, 2)
        self.assertEqual(result.succeeded_count, 1)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.next_offset, 6)
        list_records.assert_called_once_with(self.session, limit=2, offset=4)

    @patch("app.services.vector_backfill.sync_market_observation_vector")
    @patch("app.services.vector_backfill.list_observations_for_vector_backfill")
    def test_last_partial_batch_has_no_next_offset(self, list_records, sync):
        list_records.return_value = [MagicMock()]

        with patch.dict(os.environ, VECTOR_ENVIRONMENT):
            result = backfill_market_observation_vectors(
                self.session,
                limit=25,
                offset=0,
            )

        self.assertEqual(result.next_offset, None)
        sync.assert_called_once()

    def test_disabled_sync_is_rejected_before_database_read(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(VectorBackfillNotConfiguredError):
                backfill_market_observation_vectors(
                    self.session,
                    limit=25,
                    offset=0,
                )

        self.session.scalars.assert_not_called()


if __name__ == "__main__":
    unittest.main()

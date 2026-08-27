import os
import unittest
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from app.models.market_price_observation import MarketPriceObservation
from app.services.huggingface_embeddings import EmbeddingError, create_embedding
from app.services.market_vector_sync import (
    observation_embedding_text,
    vector_sync_enabled,
)
from app.services.pinecone_vector_store import (
    query_observation_vectors,
    upsert_observation_vector,
)


def observation() -> MarketPriceObservation:
    return MarketPriceObservation(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        product_name="dell latitude 5440",
        manufacturer="dell",
        product_line="latitude",
        model_number="5440",
        cpu="intel core i5",
        ram_gb=16,
        storage_capacity_gb=512,
        storage_type="ssd",
        condition="new",
        supplier_name="Example Supplier",
        quantity=1,
        unit_price=850000,
        currency="NGN",
        source_name="Example Market",
        observation_date=date(2026, 8, 26),
        source_reliability=0.7,
        location_country="Nigeria",
    )


class _EmbeddingResult(list):
    def tolist(self):
        return list(self)


class MarketVectorSyncTests(unittest.TestCase):
    def test_embedding_text_is_stable_and_excludes_price(self) -> None:
        text = observation_embedding_text(observation())

        self.assertIn("product: dell latitude 5440", text)
        self.assertIn("memory: 16GB RAM", text)
        self.assertNotIn("850000", text)

    def test_embedding_dimension_is_validated(self) -> None:
        client = MagicMock()
        client.feature_extraction.return_value = _EmbeddingResult([0.1] * 384)
        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
            result = create_embedding("example", client_factory=lambda _: client)

        self.assertEqual(len(result), 384)

    def test_wrong_embedding_dimension_is_rejected(self) -> None:
        client = MagicMock()
        client.feature_extraction.return_value = _EmbeddingResult([0.1] * 10)
        with patch.dict(os.environ, {"HF_TOKEN": "test-token"}):
            with self.assertRaisesRegex(EmbeddingError, "dimension"):
                create_embedding("example", client_factory=lambda _: client)

    def test_vector_uses_observation_id_and_safe_metadata(self) -> None:
        client = MagicMock()
        client.describe_index.return_value.host = "index.example"
        index = client.Index.return_value
        environment = {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_INDEX_NAME": "procurement-laptops",
            "PINECONE_NAMESPACE": "market-observations",
        }

        with patch.dict(os.environ, environment):
            upsert_observation_vector(
                observation(),
                [0.1] * 384,
                client_factory=lambda _: client,
            )

        vector = index.upsert.call_args.kwargs["vectors"][0]
        self.assertEqual(vector["id"], "11111111-1111-1111-1111-111111111111")
        self.assertNotIn("unit_price", vector["metadata"])
        self.assertEqual(
            index.upsert.call_args.kwargs["namespace"],
            "market-observations",
        )

    def test_vector_sync_is_disabled_by_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(vector_sync_enabled())

    def test_vector_query_filters_and_rejects_low_scores(self) -> None:
        accepted_id = "11111111-1111-1111-1111-111111111111"
        client = MagicMock()
        client.describe_index.return_value.host = "index.example"
        index = client.Index.return_value
        index.query.return_value.matches = [
            MagicMock(id=accepted_id, score=0.91),
            MagicMock(id="22222222-2222-2222-2222-222222222222", score=0.60),
            MagicMock(id="not-an-observation-id", score=0.99),
        ]
        environment = {
            "PINECONE_API_KEY": "test-key",
            "PINECONE_INDEX_NAME": "procurement-laptops",
            "PINECONE_NAMESPACE": "market-observations",
        }

        with patch.dict(os.environ, environment):
            matches = query_observation_vectors(
                [0.1] * 384,
                condition="new",
                currency="NGN",
                top_k=10,
                minimum_similarity=0.70,
                client_factory=lambda _: client,
            )

        self.assertEqual(str(matches[0][0]), accepted_id)
        self.assertEqual(matches[0][1], 0.91)
        self.assertEqual(len(matches), 1)
        self.assertEqual(
            index.query.call_args.kwargs["filter"],
            {"condition": "new", "currency": "NGN"},
        )


if __name__ == "__main__":
    unittest.main()

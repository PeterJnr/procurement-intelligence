import os
import unittest
from unittest.mock import patch

from app.config import cors_allowed_origins, validate_configuration


CORE_ENVIRONMENT = {
    "DATABASE_URL": "postgresql+psycopg://example",
    "MARKET_ADMIN_API_KEY": "test-key",
    "ENABLE_MARKET_SCHEDULER": "false",
}


class ConfigurationTests(unittest.TestCase):
    def test_minimal_core_configuration_is_valid(self) -> None:
        with patch.dict(os.environ, CORE_ENVIRONMENT, clear=True):
            self.assertIsNone(validate_configuration())

    def test_enabled_semantic_retrieval_requires_external_settings(self) -> None:
        environment = {
            **CORE_ENVIRONMENT,
            "ENABLE_SEMANTIC_RETRIEVAL": "true",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Semantic retrieval requires"):
                validate_configuration()

    def test_invalid_similarity_threshold_is_rejected(self) -> None:
        environment = {
            **CORE_ENVIRONMENT,
            "ENABLE_SEMANTIC_RETRIEVAL": "true",
            "HF_TOKEN": "token",
            "HF_EMBEDDING_MODEL": "model",
            "PINECONE_API_KEY": "key",
            "PINECONE_INDEX_NAME": "index",
            "PINECONE_NAMESPACE": "namespace",
            "PINECONE_MIN_SIMILARITY": "1.5",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "between 0 and 1"):
                validate_configuration()

    def test_cors_origins_are_normalized_without_wildcards(self) -> None:
        with patch.dict(
            os.environ,
            {"CORS_ALLOWED_ORIGINS": "http://localhost:3000/, https://app.test"},
        ):
            self.assertEqual(
                cors_allowed_origins(),
                ["http://localhost:3000", "https://app.test"],
            )
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "*"}):
            with self.assertRaisesRegex(RuntimeError, "Wildcard"):
                cors_allowed_origins()


if __name__ == "__main__":
    unittest.main()

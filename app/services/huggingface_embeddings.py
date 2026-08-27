import os
from collections.abc import Callable
from typing import Any

from huggingface_hub import InferenceClient


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMENSION = 384


class EmbeddingError(RuntimeError):
    pass


def _create_client(token: str) -> InferenceClient:
    return InferenceClient(provider="auto", api_key=token, timeout=30)


def create_embedding(
    text: str,
    *,
    client_factory: Callable[[str], Any] = _create_client,
) -> list[float]:
    """Create and validate one dense product embedding."""
    token = os.getenv("HF_TOKEN")
    if not token:
        raise EmbeddingError("HF_TOKEN is not configured")

    model = os.getenv("HF_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    try:
        result = client_factory(token).feature_extraction(text, model=model)
        values = result.tolist() if hasattr(result, "tolist") else result
        if values and isinstance(values[0], list):
            values = values[0]
        embedding = [float(value) for value in values]
    except Exception as error:
        raise EmbeddingError("Hugging Face could not create an embedding") from error

    expected_dimension = int(
        os.getenv("PINECONE_EMBEDDING_DIMENSION", str(DEFAULT_EMBEDDING_DIMENSION))
    )
    if len(embedding) != expected_dimension:
        raise EmbeddingError(
            f"Embedding dimension {len(embedding)} does not match "
            f"configured dimension {expected_dimension}"
        )
    if not all(value == value and abs(value) != float("inf") for value in embedding):
        raise EmbeddingError("Embedding contains non-finite values")
    return embedding

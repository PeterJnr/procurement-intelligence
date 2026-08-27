import os
import uuid
from collections.abc import Callable
from typing import Any

from pinecone import Pinecone

from app.models.market_price_observation import MarketPriceObservation


class VectorStoreError(RuntimeError):
    pass


def _create_client(api_key: str) -> Pinecone:
    return Pinecone(api_key=api_key)


def _metadata(observation: MarketPriceObservation) -> dict[str, Any]:
    values = {
        "observation_id": str(observation.id),
        "product_name": observation.product_name,
        "manufacturer": observation.manufacturer,
        "product_line": observation.product_line,
        "model_number": observation.model_number,
        "cpu": observation.cpu,
        "ram_gb": observation.ram_gb,
        "storage_capacity_gb": observation.storage_capacity_gb,
        "storage_type": observation.storage_type,
        "condition": observation.condition,
        "currency": observation.currency,
        "source_name": observation.source_name,
        "observation_date": observation.observation_date.isoformat(),
    }
    return {key: value for key, value in values.items() if value is not None}


def upsert_observation_vector(
    observation: MarketPriceObservation,
    embedding: list[float],
    *,
    client_factory: Callable[[str], Any] = _create_client,
) -> None:
    """Upsert searchable identity metadata; PostgreSQL retains the price truth."""
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    namespace = os.getenv("PINECONE_NAMESPACE")
    if not api_key or not index_name or not namespace:
        raise VectorStoreError("Pinecone configuration is incomplete")

    try:
        client = client_factory(api_key)
        description = client.describe_index(index_name)
        index = client.Index(host=description.host)
        index.upsert(
            vectors=[
                {
                    "id": str(observation.id),
                    "values": embedding,
                    "metadata": _metadata(observation),
                }
            ],
            namespace=namespace,
        )
    except Exception as error:
        raise VectorStoreError("Pinecone could not store the observation vector") from error


def query_observation_vectors(
    embedding: list[float],
    *,
    condition: str,
    currency: str,
    top_k: int,
    minimum_similarity: float,
    client_factory: Callable[[str], Any] = _create_client,
) -> list[tuple[uuid.UUID, float]]:
    """Return qualified vector IDs and scores without treating metadata as truth."""
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    namespace = os.getenv("PINECONE_NAMESPACE")
    if not api_key or not index_name or not namespace:
        raise VectorStoreError("Pinecone configuration is incomplete")

    try:
        client = client_factory(api_key)
        description = client.describe_index(index_name)
        response = client.Index(host=description.host).query(
            vector=embedding,
            top_k=top_k,
            namespace=namespace,
            filter={"condition": condition, "currency": currency},
            include_metadata=False,
        )
        matches = []
        for match in response.matches:
            if match.score < minimum_similarity:
                continue
            try:
                matches.append((uuid.UUID(match.id), float(match.score)))
            except ValueError:
                continue
        return matches
    except Exception as error:
        raise VectorStoreError("Pinecone could not query observation vectors") from error

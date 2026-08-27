import os

from app.models.market_price_observation import MarketPriceObservation
from app.services.huggingface_embeddings import create_embedding
from app.services.pinecone_vector_store import upsert_observation_vector


def vector_sync_enabled() -> bool:
    return os.getenv("ENABLE_VECTOR_SYNC", "false").casefold() in {
        "true",
        "1",
        "yes",
    }


def observation_embedding_text(observation: MarketPriceObservation) -> str:
    """Build a stable semantic description without copying authoritative price."""
    fields = [
        ("product", observation.product_name),
        ("manufacturer", observation.manufacturer),
        ("product line", observation.product_line),
        ("model", observation.model_number),
        ("processor", observation.cpu),
        ("memory", f"{observation.ram_gb}GB RAM"),
        (
            "storage",
            f"{observation.storage_capacity_gb}GB {observation.storage_type}",
        ),
        ("condition", observation.condition),
    ]
    return "; ".join(f"{label}: {value}" for label, value in fields if value is not None)


def sync_market_observation_vector(observation: MarketPriceObservation) -> None:
    embedding = create_embedding(observation_embedding_text(observation))
    upsert_observation_vector(observation, embedding)

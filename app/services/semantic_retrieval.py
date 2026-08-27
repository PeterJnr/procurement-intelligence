import os

from sqlalchemy.orm import Session

from app.models.normalized_laptop import NormalizedLaptop
from app.repositories.market_price_observation import find_observations_by_ids
from app.services.huggingface_embeddings import create_embedding
from app.services.pinecone_vector_store import query_observation_vectors


def semantic_retrieval_enabled() -> bool:
    return os.getenv("ENABLE_SEMANTIC_RETRIEVAL", "false").casefold() in {
        "true",
        "1",
        "yes",
    }


def normalized_laptop_embedding_text(product: NormalizedLaptop) -> str:
    fields = [
        ("product", product.product_name),
        ("manufacturer", product.manufacturer),
        ("product line", product.product_line),
        ("model", product.model_number),
        ("processor", product.cpu),
        ("memory", f"{product.ram_gb}GB RAM" if product.ram_gb else None),
        (
            "storage",
            f"{product.storage_capacity_gb}GB {product.storage_type}"
            if product.storage_capacity_gb
            else None,
        ),
        ("condition", product.condition),
    ]
    return "; ".join(f"{label}: {value}" for label, value in fields if value is not None)


def find_semantic_observations(
    session: Session,
    product: NormalizedLaptop,
    currency: str,
) -> tuple[list, dict]:
    """Find semantic candidates, then resolve their authoritative DB records."""
    if not semantic_retrieval_enabled():
        return [], {}

    minimum_similarity = float(os.getenv("PINECONE_MIN_SIMILARITY", "0.65"))
    if not 0 <= minimum_similarity <= 1:
        raise RuntimeError("PINECONE_MIN_SIMILARITY must be between 0 and 1")
    top_k = int(os.getenv("PINECONE_SEMANTIC_TOP_K", "10"))
    if not 1 <= top_k <= 50:
        raise RuntimeError("PINECONE_SEMANTIC_TOP_K must be between 1 and 50")

    embedding = create_embedding(normalized_laptop_embedding_text(product))
    matches = query_observation_vectors(
        embedding,
        condition=product.condition,
        currency=currency,
        top_k=top_k,
        minimum_similarity=minimum_similarity,
    )
    ids = [observation_id for observation_id, _ in matches]
    scores = dict(matches)
    return find_observations_by_ids(session, ids), scores

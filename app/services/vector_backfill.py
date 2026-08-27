import os

from sqlalchemy.orm import Session

from app.models.vector_backfill import VectorBackfillResponse
from app.repositories.market_price_observation import (
    list_observations_for_vector_backfill,
)
from app.services.market_vector_sync import (
    sync_market_observation_vector,
    vector_sync_enabled,
)


REQUIRED_VECTOR_SETTINGS = (
    "HF_TOKEN",
    "HF_EMBEDDING_MODEL",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
    "PINECONE_NAMESPACE",
)


class VectorBackfillNotConfiguredError(RuntimeError):
    pass


def _ensure_vector_sync_configured() -> None:
    missing = [name for name in REQUIRED_VECTOR_SETTINGS if not os.getenv(name)]
    if not vector_sync_enabled() or missing:
        raise VectorBackfillNotConfiguredError(
            "Vector synchronization is not fully configured or enabled"
        )


def backfill_market_observation_vectors(
    session: Session,
    *,
    limit: int,
    offset: int,
) -> VectorBackfillResponse:
    """Synchronize one stable, bounded page of existing observations."""
    _ensure_vector_sync_configured()
    observations = list_observations_for_vector_backfill(
        session,
        limit=limit,
        offset=offset,
    )
    succeeded_count = 0
    failed_count = 0
    for observation in observations:
        try:
            sync_market_observation_vector(observation)
            succeeded_count += 1
        except Exception:
            failed_count += 1

    processed_count = len(observations)
    return VectorBackfillResponse(
        requested_limit=limit,
        offset=offset,
        processed_count=processed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        next_offset=offset + processed_count if processed_count == limit else None,
    )

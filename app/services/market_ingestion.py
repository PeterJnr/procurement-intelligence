import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.market_ingestion import MarketIngestionResult
from app.models.market_observation_candidate import MarketObservationCandidate
from app.models.market_price_observation_schema import MarketPriceObservationCreate
from app.repositories.market_price_observation import upsert_market_price_observation
from app.services.jumia_collector import collect_and_enrich_jumia_candidates
from app.services.kara_collector import collect_kara_candidates
from app.services.market_vector_sync import (
    sync_market_observation_vector,
    vector_sync_enabled,
)
from app.services.weford_collector import collect_weford_candidates


JUMIA_INITIAL_RELIABILITY = Decimal("0.60")
KARA_INITIAL_RELIABILITY = Decimal("0.75")
WEFORD_INITIAL_RELIABILITY = Decimal("0.70")
logger = logging.getLogger(__name__)


def _sync_vector_if_enabled(observation) -> None:
    if not vector_sync_enabled():
        return
    try:
        sync_market_observation_vector(observation)
    except Exception:
        logger.exception(
            "Vector sync failed for market observation %s",
            observation.id,
        )


def candidate_to_observation(
    candidate: MarketObservationCandidate,
    source_reliability: Decimal = JUMIA_INITIAL_RELIABILITY,
) -> MarketPriceObservationCreate:
    """Convert only fully enriched Jumia evidence into a trusted input record."""
    if candidate.validation_status != "ready":
        raise ValueError("Candidate must be ready before it can be stored")

    product_name = " ".join(
        value
        for value in (
            candidate.manufacturer,
            candidate.product_line,
            candidate.model_number,
        )
        if value
    )

    return MarketPriceObservationCreate(
        product_name=product_name,
        manufacturer=candidate.manufacturer,
        product_line=candidate.product_line,
        model_number=candidate.model_number,
        cpu=candidate.cpu,
        ram_gb=candidate.ram_gb,
        storage_capacity_gb=candidate.storage_capacity_gb,
        storage_type=candidate.storage_type,
        condition=candidate.condition,
        supplier_name=candidate.supplier_name,
        location_city=None,
        location_country="Nigeria",
        quantity=1,
        unit_price=candidate.raw_listing.unit_price,
        currency=candidate.raw_listing.currency,
        source_name=candidate.raw_listing.source_name,
        source_url=candidate.raw_listing.source_url,
        source_external_id=candidate.raw_listing.source_external_id,
        observation_date=candidate.raw_listing.collected_at.date(),
        source_reliability=source_reliability,
        last_seen_at=candidate.raw_listing.collected_at,
    )


def ingest_jumia_observations(
    session: Session,
    product_name: str,
) -> MarketIngestionResult:
    """Collect, enrich, validate, and upsert Jumia evidence for one product."""
    candidates = collect_and_enrich_jumia_candidates(product_name)
    ready_candidates = [
        candidate for candidate in candidates if candidate.validation_status == "ready"
    ]

    created_count = 0
    updated_count = 0
    for candidate in ready_candidates:
        observation, created = upsert_market_price_observation(
            session,
            candidate_to_observation(candidate),
        )
        _sync_vector_if_enabled(observation)
        if created:
            created_count += 1
        else:
            updated_count += 1

    return MarketIngestionResult(
        collected_count=len(candidates),
        ready_count=len(ready_candidates),
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=len(candidates) - len(ready_candidates),
    )


def ingest_kara_observations(session: Session) -> MarketIngestionResult:
    """Collect and upsert explicitly configured Kara retail products."""
    candidates = collect_kara_candidates()
    ready_candidates = [
        candidate for candidate in candidates if candidate.validation_status == "ready"
    ]
    created_count = 0
    updated_count = 0
    for candidate in ready_candidates:
        observation, created = upsert_market_price_observation(
            session,
            candidate_to_observation(candidate, KARA_INITIAL_RELIABILITY),
        )
        _sync_vector_if_enabled(observation)
        created_count += int(created)
        updated_count += int(not created)

    return MarketIngestionResult(
        collected_count=len(candidates),
        ready_count=len(ready_candidates),
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=len(candidates) - len(ready_candidates),
    )


def ingest_weford_observations(session: Session) -> MarketIngestionResult:
    """Collect and upsert explicitly configured WeFord retail products."""
    candidates = collect_weford_candidates()
    ready_candidates = [
        candidate for candidate in candidates if candidate.validation_status == "ready"
    ]
    created_count = 0
    updated_count = 0
    for candidate in ready_candidates:
        observation, created = upsert_market_price_observation(
            session,
            candidate_to_observation(candidate, WEFORD_INITIAL_RELIABILITY),
        )
        _sync_vector_if_enabled(observation)
        created_count += int(created)
        updated_count += int(not created)

    return MarketIngestionResult(
        collected_count=len(candidates),
        ready_count=len(ready_candidates),
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=len(candidates) - len(ready_candidates),
    )

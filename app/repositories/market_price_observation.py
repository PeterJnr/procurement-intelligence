import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.market_price_observation import MarketPriceObservation
from app.models.market_price_observation_schema import (
    MarketPriceObservationCreate,
    MarketPriceObservationFilters,
)


def save_market_price_observation(
    session: Session,
    data: MarketPriceObservationCreate,
) -> MarketPriceObservation:
    """Persist a validated market-price observation."""
    observation, _ = upsert_market_price_observation(session, data)
    return observation


def upsert_market_price_observation(
    session: Session,
    data: MarketPriceObservationCreate,
) -> tuple[MarketPriceObservation, bool]:
    """Insert an observation or update the same source listing's daily record."""
    observation = None
    if data.source_external_id is not None:
        observation = session.scalar(
            select(MarketPriceObservation).where(
                MarketPriceObservation.source_name == data.source_name,
                MarketPriceObservation.source_external_id == data.source_external_id,
                MarketPriceObservation.observation_date == data.observation_date,
            )
        )

    created = observation is None
    if created:
        observation = MarketPriceObservation(**data.model_dump())
        session.add(observation)
    else:
        for field_name, value in data.model_dump().items():
            setattr(observation, field_name, value)

    try:
        session.commit()
        session.refresh(observation)
    except Exception:
        session.rollback()
        raise

    return observation, created


def find_comparable_observations(
    session: Session,
    filters: MarketPriceObservationFilters,
) -> list[MarketPriceObservation]:
    """Return recent observations matching all supplied product filters."""
    statement = select(MarketPriceObservation).where(
        MarketPriceObservation.condition == filters.condition,
    )
    if filters.manufacturer is not None and filters.model_number is not None:
        statement = statement.where(
            func.lower(MarketPriceObservation.manufacturer)
            == filters.manufacturer.strip().lower(),
            func.lower(MarketPriceObservation.model_number)
            == filters.model_number.strip().lower(),
        )
        if filters.product_line is not None:
            statement = statement.where(
                func.lower(MarketPriceObservation.product_line)
                == filters.product_line.strip().lower()
            )
    else:
        statement = statement.where(
            func.lower(MarketPriceObservation.product_name)
            == filters.product_name.strip().lower()
        )

    optional_filters = (
        (filters.cpu, func.lower(MarketPriceObservation.cpu), str.lower),
        (filters.ram_gb, MarketPriceObservation.ram_gb, None),
        (
            filters.storage_capacity_gb,
            MarketPriceObservation.storage_capacity_gb,
            None,
        ),
        (filters.storage_type, MarketPriceObservation.storage_type, None),
        (filters.currency, MarketPriceObservation.currency, None),
        (
            filters.location_country,
            func.lower(MarketPriceObservation.location_country),
            str.lower,
        ),
    )

    for value, column, normalizer in optional_filters:
        if value is not None:
            normalized_value = normalizer(value.strip()) if normalizer else value
            statement = statement.where(column == normalized_value)

    if filters.observed_since is not None:
        statement = statement.where(
            MarketPriceObservation.observation_date >= filters.observed_since
        )

    statement = statement.order_by(
        MarketPriceObservation.observation_date.desc(),
        MarketPriceObservation.created_at.desc(),
    ).limit(filters.limit)

    return list(session.scalars(statement).all())


def list_observations_for_vector_backfill(
    session: Session,
    *,
    limit: int,
    offset: int,
) -> list[MarketPriceObservation]:
    """Return a stable bounded page of observations for idempotent vector sync."""
    statement = (
        select(MarketPriceObservation)
        .order_by(
            MarketPriceObservation.observation_date.asc(),
            MarketPriceObservation.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def find_observations_by_ids(
    session: Session,
    observation_ids: list[uuid.UUID],
) -> list[MarketPriceObservation]:
    """Resolve vector matches to authoritative rows while preserving rank."""
    if not observation_ids:
        return []
    records = list(
        session.scalars(
            select(MarketPriceObservation).where(
                MarketPriceObservation.id.in_(observation_ids)
            )
        ).all()
    )
    records_by_id = {record.id: record for record in records}
    return [records_by_id[item_id] for item_id in observation_ids if item_id in records_by_id]

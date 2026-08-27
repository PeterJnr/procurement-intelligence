from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market_collection_run import MarketCollectionRun
from app.models.market_collection_run_schema import MarketCollectionRunFilters
from app.models.market_ingestion import MarketIngestionResult


def create_collection_run(
    session: Session,
    source_name: str,
    product_name: str | None,
) -> MarketCollectionRun:
    run = MarketCollectionRun(
        source_name=source_name,
        product_name=product_name,
        status="running",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def complete_collection_run(
    session: Session,
    run: MarketCollectionRun,
    result: MarketIngestionResult,
) -> MarketCollectionRun:
    run.status = "succeeded"
    run.completed_at = datetime.now(timezone.utc)
    for field_name, value in result.model_dump().items():
        setattr(run, field_name, value)
    session.commit()
    session.refresh(run)
    return run


def fail_collection_run(
    session: Session,
    run: MarketCollectionRun,
    error: Exception,
) -> MarketCollectionRun:
    run.status = "failed"
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = f"{type(error).__name__}: collection failed"
    session.commit()
    session.refresh(run)
    return run


def list_collection_runs(
    session: Session,
    filters: MarketCollectionRunFilters,
) -> list[MarketCollectionRun]:
    statement = select(MarketCollectionRun)
    if filters.source_name is not None:
        statement = statement.where(
            MarketCollectionRun.source_name == filters.source_name.strip()
        )
    if filters.status is not None:
        statement = statement.where(MarketCollectionRun.status == filters.status)
    statement = statement.order_by(MarketCollectionRun.started_at.desc()).limit(
        filters.limit
    )
    return list(session.scalars(statement).all())


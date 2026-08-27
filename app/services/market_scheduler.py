import logging
import os
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db_engine
from app.models.market_ingestion import MarketIngestionResult
from app.repositories.market_collection_run import (
    complete_collection_run,
    create_collection_run,
    fail_collection_run,
)
from app.services.market_ingestion import (
    ingest_jumia_observations,
    ingest_kara_observations,
    ingest_weford_observations,
)


logger = logging.getLogger(__name__)
_collection_lock = Lock()


def _run_tracked_collection(
    session: Session,
    source_name: str,
    product_name: str | None,
    collector: Callable[[], MarketIngestionResult],
) -> None:
    run = create_collection_run(session, source_name, product_name)
    try:
        result = collector()
        complete_collection_run(session, run, result)
        logger.info(
            "Market refresh completed for %s (%s): %s",
            source_name,
            product_name or "configured products",
            result.model_dump(),
        )
    except Exception as error:
        session.rollback()
        fail_collection_run(session, run, error)
        logger.exception(
            "Market refresh failed for %s (%s)",
            source_name,
            product_name or "configured products",
        )


def configured_products() -> list[str]:
    value = os.getenv("MARKET_COLLECTION_PRODUCTS", "Dell Latitude 5440")
    return [product.strip() for product in value.split(",") if product.strip()]


def weford_collection_enabled() -> bool:
    return os.getenv("ENABLE_WEFORD_COLLECTION", "false").casefold() in {
        "true",
        "1",
        "yes",
    }


def _collect_market_data() -> None:
    with Session(get_db_engine()) as session:
        for product_name in configured_products():
            _run_tracked_collection(
                session,
                "Jumia Nigeria",
                product_name,
                lambda product_name=product_name: ingest_jumia_observations(
                    session, product_name
                ),
            )

        _run_tracked_collection(
            session,
            "Kara Nigeria",
            None,
            lambda: ingest_kara_observations(session),
        )

        if weford_collection_enabled():
            _run_tracked_collection(
                session,
                "WeFord Enterprise",
                None,
                lambda: ingest_weford_observations(session),
            )


def run_market_collection_job() -> bool:
    """Run a scheduled refresh unless another refresh already owns the lock."""
    if not _collection_lock.acquire(blocking=False):
        logger.warning("Market refresh skipped because another refresh is running")
        return False
    try:
        _collect_market_data()
        return True
    finally:
        _collection_lock.release()


def _run_prelocked_market_collection() -> None:
    try:
        _collect_market_data()
    finally:
        _collection_lock.release()


def queue_market_collection(background_tasks: BackgroundTasks) -> bool:
    """Reserve the collection lock and queue one manual background refresh."""
    if not _collection_lock.acquire(blocking=False):
        return False
    try:
        background_tasks.add_task(_run_prelocked_market_collection)
    except Exception:
        _collection_lock.release()
        raise
    return True


def create_market_scheduler() -> BackgroundScheduler:
    interval_hours = int(os.getenv("MARKET_COLLECTION_INTERVAL_HOURS", "24"))
    if interval_hours < 1:
        raise RuntimeError("MARKET_COLLECTION_INTERVAL_HOURS must be at least 1")

    scheduler = BackgroundScheduler(
        timezone="UTC",
        job_defaults={"coalesce": True, "max_instances": 1},
    )
    scheduler.add_job(
        run_market_collection_job,
        trigger="interval",
        hours=interval_hours,
        id="market-data-refresh",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    return scheduler


def start_market_scheduler() -> BackgroundScheduler | None:
    enabled = os.getenv("ENABLE_MARKET_SCHEDULER", "true").casefold()
    if enabled not in {"true", "1", "yes"}:
        return None

    scheduler = create_market_scheduler()
    scheduler.start()
    return scheduler

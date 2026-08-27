from typing import Literal

from pydantic import BaseModel

from app.models.collected_market_listing import CollectedMarketListing


class MarketObservationCandidate(BaseModel):
    """Structured but not-yet-trusted evidence extracted from a raw listing."""

    raw_listing: CollectedMarketListing
    manufacturer: str | None
    product_line: str | None
    model_number: str | None
    cpu: str | None
    ram_gb: int | None
    storage_capacity_gb: int | None
    storage_type: Literal["ssd", "hdd", "emmc"] | None
    condition: Literal["new", "used", "refurbished"] | None
    supplier_name: str | None
    missing_fields: list[str]
    validation_status: Literal["ready", "needs_enrichment"]

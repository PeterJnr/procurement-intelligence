import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketPriceObservationCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    manufacturer: str = Field(min_length=1, max_length=100)
    product_line: str | None = Field(default=None, max_length=100)
    model_number: str = Field(min_length=1, max_length=100)

    cpu: str = Field(min_length=1, max_length=150)
    ram_gb: int = Field(gt=0)
    storage_capacity_gb: int = Field(gt=0)
    storage_type: Literal["ssd", "hdd", "emmc", "unknown"]
    condition: Literal["new", "used", "refurbished"]

    supplier_name: str = Field(min_length=1, max_length=200)
    location_city: str | None = Field(default=None, max_length=100)
    location_country: str = Field(min_length=1, max_length=100)

    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")

    source_name: str = Field(min_length=1, max_length=200)
    source_url: str | None = None
    source_external_id: str | None = Field(default=None, max_length=100)
    observation_date: date
    source_reliability: Decimal = Field(ge=0, le=1, decimal_places=2)
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarketPriceObservationResponse(MarketPriceObservationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class MarketPriceObservationFilters(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=100)
    product_line: str | None = Field(default=None, max_length=100)
    model_number: str | None = Field(default=None, max_length=100)
    condition: Literal["new", "used", "refurbished"]
    cpu: str | None = Field(default=None, max_length=150)
    ram_gb: int | None = Field(default=None, gt=0)
    storage_capacity_gb: int | None = Field(default=None, gt=0)
    storage_type: Literal["ssd", "hdd", "emmc", "unknown"] | None = None
    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )
    location_country: str | None = Field(default=None, max_length=100)
    observed_since: date | None = None
    limit: int = Field(default=20, ge=1, le=100)


class MarketPriceObservationListResponse(BaseModel):
    count: int
    observations: list[MarketPriceObservationResponse]

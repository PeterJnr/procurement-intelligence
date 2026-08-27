import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MarketCollectionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_name: str
    product_name: str | None
    status: Literal["running", "succeeded", "failed"]
    started_at: datetime
    completed_at: datetime | None
    collected_count: int
    ready_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    error_message: str | None


class MarketCollectionRunFilters(BaseModel):
    source_name: str | None = Field(default=None, min_length=1, max_length=200)
    status: Literal["running", "succeeded", "failed"] | None = None
    limit: int = Field(default=20, ge=1, le=100)


class MarketCollectionRunListResponse(BaseModel):
    count: int
    runs: list[MarketCollectionRunResponse]


class MarketCollectionTriggerResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    message: str

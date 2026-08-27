import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProcurementAnalysisRunFilters(BaseModel):
    product_name: str | None = Field(default=None, min_length=1, max_length=200)
    assessment: Literal["fair", "overpriced", "underpriced", "undetermined"] | None = None
    limit: int = Field(default=20, ge=1, le=100)


class ProcurementAnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_name: str
    manufacturer: str | None
    product_line: str | None
    model_number: str | None
    condition: str
    quantity: int
    quoted_price: Decimal
    currency: str
    market_data_status: str
    match_level: str
    evidence_count: int
    assessment: str
    recommended_action: str
    confidence: str
    created_at: datetime


class ProcurementAnalysisRunListResponse(BaseModel):
    count: int
    runs: list[ProcurementAnalysisRunResponse]


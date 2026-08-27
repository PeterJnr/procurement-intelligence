from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class PriceEvidenceSummary(BaseModel):
    evidence_status: Literal["no_data", "limited", "sufficient"]
    observation_count: int
    currency: str | None
    median_unit_price: Decimal | None
    lowest_unit_price: Decimal | None
    highest_unit_price: Decimal | None
    average_source_reliability: Decimal | None

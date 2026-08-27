from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CollectedMarketListing(BaseModel):
    """Raw listing collected from an external source before full validation."""

    title: str
    unit_price: Decimal
    currency: Literal["NGN"] = "NGN"
    source_name: Literal[
        "Jumia Nigeria",
        "Kara Nigeria",
        "WeFord Enterprise",
    ] = "Jumia Nigeria"
    source_url: str
    source_external_id: str | None = None
    collected_at: datetime

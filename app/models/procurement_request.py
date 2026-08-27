from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models.normalized_laptop import NormalizedLaptop


class ProductSpecifications(BaseModel):
    cpu: str | None = Field(default=None, min_length=1)
    ram: str | None = Field(default=None, min_length=1)
    storage: str | None = Field(default=None, min_length=1)


class ProcurementRequest(BaseModel):
    product: str = Field(min_length=1)
    specifications: ProductSpecifications = Field(default_factory=ProductSpecifications)
    condition: Literal["new", "used", "refurbished"]
    quantity: int = Field(gt=0)
    quoted_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(
        default="NGN",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
    )


class ProcurementRequestResponse(BaseModel):
    message: str
    request: ProcurementRequest
    normalized_product: NormalizedLaptop

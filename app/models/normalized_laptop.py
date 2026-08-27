from typing import Literal

from pydantic import BaseModel


class NormalizedLaptop(BaseModel):
    category: Literal["business_laptop"] = "business_laptop"
    product_name: str
    manufacturer: str | None
    product_line: str | None
    model_number: str | None
    cpu: str | None
    ram_gb: int | None
    storage_capacity_gb: int | None
    storage_type: Literal["ssd", "hdd", "emmc", "unknown"] | None
    condition: Literal["new", "used", "refurbished"]
    missing_fields: list[Literal["cpu", "ram", "storage"]]
    analysis_readiness: Literal["ready", "needs_more_information"]
    matching_key: str

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.procurement_request import ProcurementRequest
from app.models.procurement_analysis import ProcurementAnalysisResponse


class NaturalLanguageProcurementInput(BaseModel):
    text: str = Field(min_length=10, max_length=4000)


class ExtractedProcurementFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product: str | None
    cpu: str | None
    ram: str | None
    storage: str | None
    condition: Literal["new", "used", "refurbished"] | None
    quantity: int | None = Field(gt=0)
    # Kept as a string at the AI boundary because some hosted structured-output
    # engines cannot compile Pydantic's Decimal JSON schema.
    quoted_price: str | None
    currency: str | None = Field(min_length=3, max_length=3)


class NaturalLanguageProcurementResponse(BaseModel):
    extracted_fields: ExtractedProcurementFields
    procurement_request: ProcurementRequest | None
    missing_fields: list[str]
    ready_for_analysis: bool
    extraction_method: Literal["hugging_face"] = "hugging_face"


class NaturalLanguageProcurementAnalysisResponse(BaseModel):
    extraction: NaturalLanguageProcurementResponse
    analysis: ProcurementAnalysisResponse | None

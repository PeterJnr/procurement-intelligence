from pydantic import BaseModel


class ProductIdentity(BaseModel):
    manufacturer: str | None
    product_line: str | None
    model_number: str | None


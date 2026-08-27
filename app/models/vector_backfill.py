from pydantic import BaseModel


class VectorBackfillResponse(BaseModel):
    requested_limit: int
    offset: int
    processed_count: int
    succeeded_count: int
    failed_count: int
    next_offset: int | None

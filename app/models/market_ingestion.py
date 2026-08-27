from pydantic import BaseModel


class MarketIngestionResult(BaseModel):
    collected_count: int
    ready_count: int
    created_count: int
    updated_count: int
    skipped_count: int

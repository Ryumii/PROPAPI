"""Batch processing schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.inspect import InspectOptions, InspectResponse


class BatchItem(BaseModel):
    """Single item in a batch request."""

    id: str = Field(..., description="クライアント指定のアイテム ID", max_length=64)
    address: str | None = Field(None, examples=["東京都渋谷区渋谷2-24-12"])
    lat: float | None = Field(None, ge=20.0, le=46.0)
    lng: float | None = Field(None, ge=122.0, le=154.0)


class BatchRequest(BaseModel):
    items: list[BatchItem] = Field(..., min_length=1, max_length=1000)
    options: InspectOptions = Field(default_factory=InspectOptions)


class BatchResultItem(BaseModel):
    id: str
    status: str = Field(..., examples=["success", "error"])
    result: InspectResponse | None = None
    error: str | None = None


class BatchResponse(BaseModel):
    job_id: str
    status: str = Field(..., examples=["completed", "partial"])
    total: int
    succeeded: int
    failed: int
    results: list[BatchResultItem]

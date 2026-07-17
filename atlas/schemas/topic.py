import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    entity_type: str = Field(..., min_length=1, max_length=100)
    country: str | None = None
    source: str = "manual"
    priority: int = 0
    skip_enqueue: bool = False


class TopicResponse(BaseModel):
    id: uuid.UUID
    name: str
    entity_type: str
    country: str | None
    status: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class TopicDetailResponse(BaseModel):
    summary: str | None
    facts: list[dict]
    images: list[dict]


class TopicDiscoverRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)
    entity_type: str | None = None
    country_filter: str | None = None
    max_results: int = 20


class TopicDiscoverResponse(BaseModel):
    query: str
    entity_type: str | None
    total_found: int
    enqueued: int
    skipped: int
    results: list[dict]


class QueueItemResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    status: str
    priority: int
    retry_count: int
    source: str
    error_message: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class QueueStatsResponse(BaseModel):
    pending: int
    processing: int
    failed: int
    total: int

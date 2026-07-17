import uuid
from datetime import datetime

from pydantic import BaseModel


class VideoResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    audio_id: uuid.UUID | None
    video_path: str
    subtitle_path: str | None
    duration_seconds: float
    file_size: int
    width: int
    height: int
    codec: str
    mime_type: str
    image_count: int
    status: str
    created_at: datetime | None

    model_config = {"from_attributes": True}


class VideoGenerateResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    video_path: str
    duration_seconds: float
    file_size: int
    width: int
    height: int
    status: str

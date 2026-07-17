import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    voice: str = Field(default="hi-IN-SwaraNeural", description="Edge-TTS voice name for Hindi")
    rate: str = Field(default="+0%", description="Speaking rate adjustment (e.g. +10%, -10%)")
    pitch: str = Field(default="+0Hz", description="Pitch adjustment (e.g. +10Hz, -10Hz)")


class AudioResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    script_id: uuid.UUID | None
    audio_path: str
    duration_seconds: float
    file_size: int
    mime_type: str
    voice: str
    language: str
    created_at: datetime | None

    model_config = {"from_attributes": True}


class TTSGenerateResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    script_id: uuid.UUID | None
    audio_path: str
    duration_seconds: float
    file_size: int
    mime_type: str
    voice: str

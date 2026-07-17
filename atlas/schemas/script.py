import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ScriptGenerateRequest(BaseModel):
    script_type: str = Field(default="SHORTS_60", pattern=r"^SHORTS_\d+$")
    max_facts: int = Field(default=10, ge=1, le=25)


class ScriptResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    script_type: str
    variant: str | None
    title: str
    hook: str
    script_text: str
    estimated_duration: int
    quality_score: float | None
    readability_score: float | None
    engagement_score: float | None
    repetition_score: float | None
    parent_script_id: uuid.UUID | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class ScriptGenerateResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    script_type: str
    variant: str | None
    title: str
    hook: str
    script_text: str
    estimated_duration: int
    quality_score: float | None
    readability_score: float | None
    engagement_score: float | None
    repetition_score: float | None
    parent_script_id: uuid.UUID | None


class ScriptVariantResponse(BaseModel):
    variant: str
    title: str
    hook: str
    script_text: str
    estimated_duration: int
    quality_score: float | None
    readability_score: float | None
    engagement_score: float | None
    repetition_score: float | None
    hallucination_score: float | None = None
    grounding_score: float | None = None
    story_score: float | None = None
    language_score: float | None = None
    validation_passed: bool | None = None
    generation_attempts: int | None = None
    script_status: str | None = None


class ScriptBatchGenerateResponse(BaseModel):
    topic_id: uuid.UUID
    script_type: str
    variants: list[ScriptVariantResponse] = Field(default_factory=list)


class ScriptReportResponse(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    script_type: str
    variant: str | None
    title: str
    hook: str
    script_text: str
    estimated_duration: int
    quality_score: float | None
    readability_score: float | None
    engagement_score: float | None
    repetition_score: float | None
    hallucination_score: float | None
    grounding_score: float | None
    story_score: float | None
    language_score: float | None
    validation_passed: bool | None
    validation_report: dict | None
    generation_attempts: int | None
    script_status: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}

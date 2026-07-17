import uuid

from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin


class Script(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scripts"

    topic_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    script_type: Mapped[str] = mapped_column(String(50), nullable=False, default="SHORTS_60")
    variant: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    script_text: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    repetition_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    parent_script_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True)
    hallucination_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    grounding_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    story_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    language_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    validation_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generation_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    script_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    topic = relationship("Topic", back_populates="scripts")

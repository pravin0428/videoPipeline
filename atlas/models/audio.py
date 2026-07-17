from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin


class Audio(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audio"

    topic_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    script_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True)
    audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False, default="audio/mp3")
    voice: Mapped[str] = mapped_column(String(100), nullable=False, default="hi-IN-SwaraNeural")
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="hi-IN")

    topic = relationship("Topic", back_populates="audio")
    script = relationship("Script")

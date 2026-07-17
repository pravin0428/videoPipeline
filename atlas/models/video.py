from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin


class Video(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "videos"

    topic_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
    audio_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("audio.id", ondelete="SET NULL"), nullable=True)
    video_path: Mapped[str] = mapped_column(Text, nullable=False)
    subtitle_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width: Mapped[int] = mapped_column(Integer, nullable=False, default=1080)
    height: Mapped[int] = mapped_column(Integer, nullable=False, default=1920)
    codec: Mapped[str] = mapped_column(String(50), nullable=False, default="h264")
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False, default="video/mp4")
    image_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")

    topic = relationship("Topic", back_populates="videos")
    audio = relationship("Audio")

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin


class Image(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "images"

    topic_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license: Mapped[str | None] = mapped_column(String(100), nullable=True)

    topic = relationship("Topic", back_populates="images")

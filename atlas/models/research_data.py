from sqlalchemy import JSON as GenericJSON
from sqlalchemy import Column, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin


class ResearchData(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research_data"

    topic_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(GenericJSON, nullable=True)

    topic = relationship("Topic", back_populates="research_data")

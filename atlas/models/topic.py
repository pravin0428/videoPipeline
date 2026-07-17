from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin, UUIDMixin


class Topic(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "topics"

    name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, default="pending")

    research_data = relationship("ResearchData", back_populates="topic", cascade="all, delete-orphan")
    facts = relationship("Fact", back_populates="topic", cascade="all, delete-orphan")
    images = relationship("Image", back_populates="topic", cascade="all, delete-orphan")
    scripts = relationship("Script", back_populates="topic", cascade="all, delete-orphan")
    audio = relationship("Audio", back_populates="topic", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="topic", cascade="all, delete-orphan")

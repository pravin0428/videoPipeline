"""add videos table

Revision ID: 005
Revises: 004
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("audio_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audio.id", ondelete="SET NULL"), nullable=True),
        sa.Column("video_path", sa.Text(), nullable=False),
        sa.Column("subtitle_path", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1080"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="1920"),
        sa.Column("codec", sa.String(50), nullable=False, server_default="h264"),
        sa.Column("mime_type", sa.String(50), nullable=False, server_default="video/mp4"),
        sa.Column("image_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("videos")

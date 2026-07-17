"""add audio table

Revision ID: 003
Revises: 002
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audio",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("script_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("audio_path", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mime_type", sa.String(50), nullable=False, server_default="audio/mp3"),
        sa.Column("voice", sa.String(100), nullable=False, server_default="hi-IN-SwaraNeural"),
        sa.Column("language", sa.String(10), nullable=False, server_default="hi-IN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audio")

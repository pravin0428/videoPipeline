"""add scripts table

Revision ID: 002
Revises: 001
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("script_type", sa.String(50), nullable=False, server_default="SHORTS_60"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("script_text", sa.Text(), nullable=False),
        sa.Column("estimated_duration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("scripts")

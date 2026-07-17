"""add quality metric columns to scripts

Revision ID: 007
Revises: 006
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scripts", sa.Column("hallucination_score", sa.Float(), nullable=True))
    op.add_column("scripts", sa.Column("grounding_score", sa.Float(), nullable=True))
    op.add_column("scripts", sa.Column("story_score", sa.Float(), nullable=True))
    op.add_column("scripts", sa.Column("language_score", sa.Float(), nullable=True))
    op.add_column("scripts", sa.Column("validation_passed", sa.Boolean(), nullable=True))
    op.add_column("scripts", sa.Column("validation_report", sa.JSON(), nullable=True))
    op.add_column("scripts", sa.Column("generation_attempts", sa.Integer(), nullable=True))
    op.add_column("scripts", sa.Column("script_status", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("scripts", "script_status")
    op.drop_column("scripts", "generation_attempts")
    op.drop_column("scripts", "validation_report")
    op.drop_column("scripts", "validation_passed")
    op.drop_column("scripts", "language_score")
    op.drop_column("scripts", "story_score")
    op.drop_column("scripts", "grounding_score")
    op.drop_column("scripts", "hallucination_score")

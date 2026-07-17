"""add script variant and review metric columns

Revision ID: 006
Revises: 005
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scripts", sa.Column("variant", sa.String(50), nullable=True))
    op.add_column("scripts", sa.Column("readability_score", sa.Float(), nullable=True))
    op.add_column("scripts", sa.Column("engagement_score", sa.Float(), nullable=True))
    op.add_column("scripts", sa.Column("repetition_score", sa.Float(), nullable=True))
    op.add_column("scripts", sa.Column("parent_script_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True))


def downgrade() -> None:
    op.drop_column("scripts", "variant")
    op.drop_column("scripts", "readability_score")
    op.drop_column("scripts", "engagement_score")
    op.drop_column("scripts", "repetition_score")
    op.drop_column("scripts", "parent_script_id")

"""날짜별 영업시간 예외(임시휴무 등) 테이블

Revision ID: a7d1e4f63b29
Revises: f6c9d3e52a18
Create Date: 2026-11-28 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7d1e4f63b29"
down_revision: Union[str, None] = "f6c9d3e52a18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_hours_exceptions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("place_id", sa.String(length=50), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("open_time", sa.Time(), nullable=True),
        sa.Column("close_time", sa.Time(), nullable=True),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["place_id"], ["places.kakao_place_id"]),
        sa.PrimaryKeyConstraint("user_id", "place_id", "date"),
    )


def downgrade() -> None:
    op.drop_table("business_hours_exceptions")

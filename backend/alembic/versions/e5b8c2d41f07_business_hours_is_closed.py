"""business_hours 휴무일(is_closed) 지원

Revision ID: e5b8c2d41f07
Revises: d4a7e1b92c03
Create Date: 2026-11-28 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5b8c2d41f07"
down_revision: Union[str, None] = "d4a7e1b92c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "business_hours",
        sa.Column("is_closed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.alter_column("business_hours", "open_time", existing_type=sa.Time(), nullable=True)
    op.alter_column("business_hours", "close_time", existing_type=sa.Time(), nullable=True)


def downgrade() -> None:
    # 휴무 행은 시간이 없으므로 되돌리기 전에 삭제합니다.
    op.execute("DELETE FROM business_hours WHERE is_closed")
    op.alter_column("business_hours", "close_time", existing_type=sa.Time(), nullable=False)
    op.alter_column("business_hours", "open_time", existing_type=sa.Time(), nullable=False)
    op.drop_column("business_hours", "is_closed")

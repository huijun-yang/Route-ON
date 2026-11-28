"""course_stops 이동시간 출처(travel_source) 저장

Revision ID: f6c9d3e52a18
Revises: e5b8c2d41f07
Create Date: 2026-11-28 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6c9d3e52a18"
down_revision: Union[str, None] = "e5b8c2d41f07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "course_stops",
        sa.Column("travel_source", sa.String(length=20), server_default="unknown", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("course_stops", "travel_source")

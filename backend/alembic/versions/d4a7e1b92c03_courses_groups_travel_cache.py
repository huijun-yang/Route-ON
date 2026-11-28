"""courses 결과 필드, 분 단위 시각, 그룹 제목, 이동시간 캐시, 활성 코스 유일 제약

Revision ID: d4a7e1b92c03
Revises: 8411b41d91d1
Create Date: 2026-11-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4a7e1b92c03"
down_revision: Union[str, None] = "8411b41d91d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- courses: 계산 결과와 재현에 필요한 입력 ---
    op.add_column("courses", sa.Column("status", sa.String(length=20), server_default="OK", nullable=False))
    op.add_column("courses", sa.Column("start_lat", sa.Float(), nullable=True))
    op.add_column("courses", sa.Column("start_lng", sa.Float(), nullable=True))
    for name in ("start_min", "end_min", "total_travel_min", "total_walk_min", "total_walk_m", "total_fare"):
        op.add_column("courses", sa.Column(name, sa.Integer(), server_default="0", nullable=False))
    op.add_column("courses", sa.Column("excluded", sa.JSON(), nullable=True))

    # 같은 group_id 안에서 활성 코스는 하나만. (기존 데이터에 중복이 있으면 가장 먼저 만든 것만 남김)
    op.execute(
        """
        UPDATE courses SET is_active = FALSE
        WHERE is_active AND id NOT IN (
            SELECT DISTINCT ON (group_id) id FROM courses WHERE is_active
            ORDER BY group_id, created_at, id
        )
        """
    )
    op.create_index(
        "uq_courses_one_active_per_group",
        "courses",
        ["group_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    # --- course_stops: Time 컬럼 → 분(int). 자정을 넘는 시각(1440 이상)을 담기 위함 ---
    op.add_column("course_stops", sa.Column("arrival_min", sa.Integer(), nullable=True))
    op.add_column("course_stops", sa.Column("start_min", sa.Integer(), nullable=True))
    op.add_column("course_stops", sa.Column("departure_min", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE course_stops SET
          arrival_min = CASE WHEN arrival_time IS NULL THEN NULL
                        ELSE (EXTRACT(HOUR FROM arrival_time) * 60 + EXTRACT(MINUTE FROM arrival_time))::int END,
          departure_min = CASE WHEN departure_time IS NULL THEN NULL
                          ELSE (EXTRACT(HOUR FROM departure_time) * 60 + EXTRACT(MINUTE FROM departure_time))::int END
        """
    )
    op.execute("UPDATE course_stops SET start_min = arrival_min")
    op.drop_column("course_stops", "arrival_time")
    op.drop_column("course_stops", "departure_time")
    for name in ("travel_min", "wait_min", "walk_min", "walk_m", "fare"):
        op.add_column("course_stops", sa.Column(name, sa.Integer(), server_default="0", nullable=False))
    op.add_column("course_stops", sa.Column("hours", sa.JSON(), nullable=True))

    # --- group_sessions: 모임 이름 ---
    op.add_column("group_sessions", sa.Column("title", sa.String(length=100), nullable=True))

    # --- 이동시간 캐시 ---
    op.create_table(
        "travel_time_cache",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("travel_min", sa.Integer(), nullable=False),
        sa.Column("walk_min", sa.Integer(), nullable=False),
        sa.Column("walk_m", sa.Integer(), nullable=False),
        sa.Column("fare", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("travel_time_cache")
    op.drop_column("group_sessions", "title")

    op.drop_column("course_stops", "hours")
    for name in ("fare", "walk_m", "walk_min", "wait_min", "travel_min"):
        op.drop_column("course_stops", name)
    op.add_column("course_stops", sa.Column("arrival_time", sa.Time(), nullable=True))
    op.add_column("course_stops", sa.Column("departure_time", sa.Time(), nullable=True))
    op.execute(
        """
        UPDATE course_stops SET
          arrival_time = CASE WHEN arrival_min IS NULL THEN NULL
                         ELSE make_time((arrival_min / 60) % 24, arrival_min % 60, 0) END,
          departure_time = CASE WHEN departure_min IS NULL THEN NULL
                           ELSE make_time((departure_min / 60) % 24, departure_min % 60, 0) END
        """
    )
    op.drop_column("course_stops", "departure_min")
    op.drop_column("course_stops", "start_min")
    op.drop_column("course_stops", "arrival_min")

    op.drop_index("uq_courses_one_active_per_group", table_name="courses", postgresql_where=sa.text("is_active"))
    op.drop_column("courses", "excluded")
    for name in ("total_fare", "total_walk_m", "total_walk_min", "total_travel_min", "end_min", "start_min"):
        op.drop_column("courses", name)
    op.drop_column("courses", "start_lng")
    op.drop_column("courses", "start_lat")
    op.drop_column("courses", "status")

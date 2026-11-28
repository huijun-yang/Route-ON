from datetime import date as date_type

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, gen_uuid


class Course(Base, TimestampMixin):
    __tablename__ = "courses"
    __table_args__ = (
        # 같은 group_id(3개 버전 묶음) 안에서 is_active=True 는 하나만 허용합니다.
        Index(
            "uq_courses_one_active_per_group",
            "group_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    group_id: Mapped[str] = mapped_column(String(36), default=gen_uuid)  # 시간/도보/비용 3개 세트 묶음
    priority_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "time" | "walk" | "cost"
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)  # 현재 선택된 버전인지
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    share_uuid: Mapped[str] = mapped_column(String(36), default=gen_uuid, unique=True)
    course_date: Mapped[date_type] = mapped_column(Date, nullable=False)

    # --- 코스 계산 결과 / 재현에 필요한 입력 ---
    status: Mapped[str] = mapped_column(String(20), default="OK", server_default="OK")  # OK | PARTIAL | NO_FEASIBLE
    start_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_min: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # 출발 시각(0시 기준 분)
    end_min: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # 마지막 장소를 떠나는 시각(분, 1440 이상 가능)
    total_travel_min: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_walk_min: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_walk_m: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_fare: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # 대중교통 요금 합계(원)
    # 제외 추천된 장소: [{"place_id": ..., "name": ..., "reason": ...}]
    excluded: Mapped[list | None] = mapped_column(JSON, nullable=True)

    owner: Mapped["User"] = relationship(back_populates="courses")
    stops: Mapped[list["CourseStop"]] = relationship(
        back_populates="course",
        order_by="CourseStop.visit_order",
        cascade="all, delete-orphan",
    )
    group_session: Mapped["GroupSession | None"] = relationship(back_populates="course")

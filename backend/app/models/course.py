from datetime import date as date_type

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, gen_uuid


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    group_id: Mapped[str] = mapped_column(String(36), default=gen_uuid)  # 시간/도보/비용 3개 세트 묶음
    priority_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "time" | "walk" | "cost"
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)  # 현재 선택된 버전인지
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    share_uuid: Mapped[str] = mapped_column(String(36), default=gen_uuid, unique=True)
    course_date: Mapped[date_type] = mapped_column(Date, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="courses")
    stops: Mapped[list["CourseStop"]] = relationship(back_populates="course", order_by="CourseStop.visit_order")
    group_session: Mapped["GroupSession | None"] = relationship(back_populates="course")
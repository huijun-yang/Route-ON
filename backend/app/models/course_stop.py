from datetime import time

from sqlalchemy import ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, gen_uuid


class CourseStop(Base):
    __tablename__ = "course_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), nullable=False)
    place_id: Mapped[str] = mapped_column(String(50), ForeignKey("places.kakao_place_id"), nullable=False)
    visit_order: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    departure_time: Mapped[time | None] = mapped_column(Time, nullable=True)  # 출발 예상 시각
    stay_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 분 단위
    estimated_cost: Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped["Course"] = relationship(back_populates="stops")
    place: Mapped["Place"] = relationship()

from datetime import time

from sqlalchemy import ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BusinessHours(Base):
    __tablename__ = "business_hours"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    place_id: Mapped[str] = mapped_column(String(50), ForeignKey("places.kakao_place_id"), primary_key=True)
    weekday: Mapped[int] = mapped_column(primary_key=True)  # 0=월 ~ 6=일
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)
    # 브레이크타임 (없으면 둘 다 비워둠)
    break_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_end: Mapped[time | None] = mapped_column(Time, nullable=True)

    user: Mapped["User"] = relationship(back_populates="business_hours")
    place: Mapped["Place"] = relationship(back_populates="business_hours")

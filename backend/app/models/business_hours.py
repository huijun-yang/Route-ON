from datetime import time

from sqlalchemy import Boolean, ForeignKey, String, Time, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BusinessHours(Base):
    __tablename__ = "business_hours"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    place_id: Mapped[str] = mapped_column(String(50), ForeignKey("places.kakao_place_id"), primary_key=True)
    weekday: Mapped[int] = mapped_column(primary_key=True)  # 0=월 ~ 6=일
    # 휴무일(is_closed=True)이면 open_time/close_time 은 비워둡니다.
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    # 브레이크타임 (없으면 둘 다 비워둠)
    break_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_end: Mapped[time | None] = mapped_column(Time, nullable=True)

    user: Mapped["User"] = relationship(back_populates="business_hours")
    place: Mapped["Place"] = relationship(back_populates="business_hours")

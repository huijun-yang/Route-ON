from datetime import date as date_type
from datetime import time

from sqlalchemy import Boolean, Date, ForeignKey, String, Time, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BusinessHoursException(Base):
    """특정 날짜에만 적용되는 영업시간 (임시휴무, 특별 영업). 요일별 BusinessHours 보다 우선합니다."""

    __tablename__ = "business_hours_exceptions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    place_id: Mapped[str] = mapped_column(String(50), ForeignKey("places.kakao_place_id"), primary_key=True)
    date: Mapped[date_type] = mapped_column(Date, primary_key=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_end: Mapped[time | None] = mapped_column(Time, nullable=True)

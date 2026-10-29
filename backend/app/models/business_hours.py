from sqlalchemy import ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BusinessHours(Base):
    __tablename__ = "business_hours"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    place_id: Mapped[str] = mapped_column(String(50), ForeignKey("places.kakao_place_id"), primary_key=True)
    weekday: Mapped[int] = mapped_column(primary_key=True)  # 0=월 ~ 6=일
    open_time: Mapped[str] = mapped_column(Time, nullable=False)
    close_time: Mapped[str] = mapped_column(Time, nullable=False)

    user: Mapped["User"] = relationship(back_populates="business_hours")
    place: Mapped["Place"] = relationship(back_populates="business_hours")
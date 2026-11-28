from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, gen_uuid


class TravelTimeCache(Base):
    """Tmap 이동시간 조회 결과 캐시. (출발 좌표, 도착 좌표, 요일/시간대) 단위.

    추정값(직선거리 기반)은 저장하지 않습니다. 실제 API 결과만 저장해서
    같은 구간을 다시 조회할 때 외부 API 호출을 줄입니다.
    """

    __tablename__ = "travel_time_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    travel_min: Mapped[int] = mapped_column(Integer, nullable=False)
    walk_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    walk_m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fare: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, gen_uuid


class CourseStop(Base):
    """코스의 방문 1건. 모든 시각은 '출발일 0시부터 지난 분'이며 자정을 넘기면 1440 이상입니다."""

    __tablename__ = "course_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), nullable=False)
    place_id: Mapped[str] = mapped_column(String(50), ForeignKey("places.kakao_place_id"), nullable=False)
    visit_order: Mapped[int] = mapped_column(Integer, nullable=False)

    arrival_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 도착 시각
    start_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 실제 체류 시작(영업 시작까지 대기 후)
    departure_min: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 출발 예상 시각
    stay_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 분 단위
    estimated_cost: Mapped[int] = mapped_column(Integer, default=0)  # 사용자가 입력한 장소 지출 예상(원)

    # 이전 장소(또는 출발지)에서 여기까지 오는 구간 정보
    travel_min: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    wait_min: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    walk_min: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    walk_m: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    fare: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # 이 구간 이동시간의 출처: "tmap" | "cache" | "estimate"(직선거리 추정) | "same" | "unknown"(과거 데이터)
    travel_source: Mapped[str] = mapped_column(String(20), default="unknown", server_default="unknown")

    # 코스 계산에 실제로 쓴 영업시간 기록 (재계획 때 같은 조건으로 다시 계산하기 위함)
    # {"open": "10:00", "close": "22:00", "break_start": null, "break_end": null, "source": "saved"|"inline"|"assumed"}
    hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    course: Mapped["Course"] = relationship(back_populates="stops")
    place: Mapped["Place"] = relationship()

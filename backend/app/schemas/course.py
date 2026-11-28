from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.schemas.place import PlaceRead

# 우선순위 3버전: 이동시간 / 도보량 / 교통비
PriorityType = Literal["time", "walk", "cost"]
CourseStatus = Literal["OK", "PARTIAL", "NO_FEASIBLE"]

PRIORITY_LABEL = {"time": "최단 시간", "walk": "최소 도보", "cost": "최저 비용"}
DAY_MIN = 1440


def fmt_minutes(minutes: int | None) -> tuple[str | None, int]:
    """분 → ("HH:MM", 일수 오프셋). 1560 → ("02:00", 1)"""
    if minutes is None:
        return None, 0
    return f"{(minutes % DAY_MIN) // 60:02d}:{minutes % 60:02d}", minutes // DAY_MIN


def parse_hhmm(value: str) -> int:
    h, m = value.split(":")
    return int(h) * 60 + int(m)


# ---------------------------------------------------------------- 요청 ----------


class HoursOverride(BaseModel):
    """이번 코스 계산에만 쓰는 영업시간. 저장된 영업시간보다 우선합니다. (open == close 면 24시간, is_closed 면 휴무)"""

    is_closed: bool = False
    open_time: time | None = None
    close_time: time | None = None
    break_start: time | None = None
    break_end: time | None = None

    @model_validator(mode="after")
    def check_break(self):
        if self.is_closed:
            if any(v is not None for v in (self.open_time, self.close_time, self.break_start, self.break_end)):
                raise ValueError("휴무일(is_closed=true)에는 영업시간/브레이크타임을 입력할 수 없습니다")
            return self
        if self.open_time is None or self.close_time is None:
            raise ValueError("open_time 과 close_time 은 휴무일이 아니면 필수입니다")
        if (self.break_start is None) != (self.break_end is None):
            raise ValueError("break_start 와 break_end 는 함께 입력하거나 둘 다 비워야 합니다")
        return self


class StopInput(BaseModel):
    place_id: str = Field(min_length=1, max_length=50, description="먼저 POST /places 로 저장한 장소의 kakao_place_id")
    stay_min: int | None = Field(default=None, ge=5, le=720, description="체류시간(분). 비우면 장소 유형별 추천값을 씁니다")
    estimated_cost: int = Field(default=0, ge=0, le=10_000_000, description="이 장소에서 쓸 예상 지출(원)")
    hours: HoursOverride | None = None


class StartPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class CourseCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=80)
    course_date: date
    start: StartPoint
    start_time: time = Field(description="출발 시각 (예: 10:00)")
    stops: list[StopInput] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def no_duplicates(self):
        ids = [s.place_id for s in self.stops]
        if len(set(ids)) != len(ids):
            raise ValueError("같은 장소를 두 번 넣을 수 없습니다")
        return self


class ReplanRequest(BaseModel):
    """진행 중인 코스를 현재 위치·시각 기준으로 다시 계산합니다."""

    current_time: time
    current_lat: float = Field(ge=-90, le=90)
    current_lng: float = Field(ge=-180, le=180)
    visited_place_ids: list[str] = Field(default_factory=list, description="이미 방문을 끝낸 장소")
    stay_adjustments: dict[str, int] = Field(
        default_factory=dict, description="장소별 체류시간 증감(분). 예: {'12345': 30} = 30분 더 머무르기"
    )


class CourseUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=80)


# ---------------------------------------------------------------- 응답 ----------


class HoursSnapshot(BaseModel):
    closed: bool = False  # True 면 그날은 휴무 (open/close 없음)
    open: str | None = None
    close: str | None = None
    break_start: str | None = None
    break_end: str | None = None
    source: Literal["saved", "inline", "assumed", "exception"]


class ExcludedRead(BaseModel):
    place_id: str
    name: str | None = None
    reason: str  # WINDOW_TOO_SHORT | ALREADY_CLOSED | UNREACHABLE_IN_TIME


class CourseStopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    visit_order: int
    arrival_min: int | None = None
    start_min: int | None = None
    departure_min: int | None = None
    stay_duration: int | None = None  # 분
    estimated_cost: int = 0
    travel_min: int = 0
    wait_min: int = 0
    walk_min: int = 0
    walk_m: int = 0
    fare: int = 0
    travel_source: str = "unknown"  # tmap | cache | estimate | same | unknown
    hours: HoursSnapshot | None = None
    place: PlaceRead

    @computed_field
    @property
    def arrival_time(self) -> str | None:
        return fmt_minutes(self.arrival_min)[0]

    @computed_field
    @property
    def start_time(self) -> str | None:
        return fmt_minutes(self.start_min)[0]

    @computed_field
    @property
    def departure_time(self) -> str | None:
        return fmt_minutes(self.departure_min)[0]

    @computed_field
    @property
    def arrival_day_offset(self) -> int:
        return fmt_minutes(self.arrival_min)[1]

    @computed_field
    @property
    def departure_day_offset(self) -> int:
        return fmt_minutes(self.departure_min)[1]


def fatigue_of(total_walk_m: int, total_travel_min: int, stop_count: int) -> tuple[float, str]:
    """피로도 어림값. 도보(km) + 이동(시간) + 방문 장소 수×0.5 점."""
    score = round(total_walk_m / 1000 + total_travel_min / 60 + 0.5 * stop_count, 1)
    if score < 3:
        return score, "여유로움"
    if score < 5:
        return score, "보통"
    return score, "높음"


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    group_id: str  # 같은 요청에서 만든 3개 버전을 묶는 ID
    priority_type: PriorityType
    is_active: bool
    title: str
    share_uuid: str
    course_date: date
    created_at: datetime
    status: CourseStatus = "OK"
    start_lat: float | None = None
    start_lng: float | None = None
    start_min: int = 0
    end_min: int = 0
    total_travel_min: int = 0
    total_walk_min: int = 0
    total_walk_m: int = 0
    total_fare: int = 0
    excluded: list[ExcludedRead] | None = None
    stops: list[CourseStopRead] = []

    # 프론트 PriorityView 가 쓰는 이름들
    @computed_field
    @property
    def total_time(self) -> int:
        """출발부터 마지막 장소를 떠날 때까지(분)"""
        return max(0, self.end_min - self.start_min)

    @computed_field
    @property
    def total_walk(self) -> int:
        """총 도보량(m)"""
        return self.total_walk_m

    @computed_field
    @property
    def total_cost(self) -> int:
        """교통비 + 장소별 예상 지출(원)"""
        return self.total_fare + sum(s.estimated_cost for s in self.stops)

    @computed_field
    @property
    def fatigue_score(self) -> float:
        return fatigue_of(self.total_walk_m, self.total_travel_min, len(self.stops))[0]

    @computed_field
    @property
    def fatigue_level(self) -> str:
        return fatigue_of(self.total_walk_m, self.total_travel_min, len(self.stops))[1]

    @computed_field
    @property
    def has_estimated_travel(self) -> bool:
        """일부 구간 이동시간이 직선거리 추정값인지 (저장된 코스를 나중에 조회해도 알 수 있음)"""
        return any(s.travel_source == "estimate" for s in self.stops)

    @computed_field
    @property
    def priority_label(self) -> str:
        return PRIORITY_LABEL.get(self.priority_type, self.priority_type)

    @computed_field
    @property
    def end_time(self) -> str:
        return fmt_minutes(self.end_min)[0] or "00:00"

    @computed_field
    @property
    def end_day_offset(self) -> int:
        return fmt_minutes(self.end_min)[1]


class CourseSummary(BaseModel):
    """히스토리 목록용 요약."""

    id: str
    group_id: str
    title: str
    course_date: date
    created_at: datetime
    priority_type: PriorityType
    is_active: bool
    status: CourseStatus
    total_time: int
    total_cost: int
    stop_count: int
    place_names: list[str]


class CoursePlanResponse(BaseModel):
    """코스 생성/재계획 결과: 우선순위별 3개 버전."""

    group_id: str
    courses: list[CourseRead]
    warnings: list[str] = []

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.place import PlaceRead

# 우선순위 3버전: 이동시간 / 도보량 / 교통비
PriorityType = Literal["time", "walk", "cost"]


class CourseStopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    visit_order: int
    arrival_time: time | None = None
    stay_duration: int | None = None  # 분
    estimated_cost: int = 0
    place: PlaceRead


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
    stops: list[CourseStopRead] = []

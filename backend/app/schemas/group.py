from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator

from app.schemas.course import StartPoint, ensure_not_past
from app.schemas.place import PlaceRead


class GroupCreate(BaseModel):
    title: str | None = Field(default=None, max_length=100)


class GroupJoin(BaseModel):
    invite_code: str = Field(min_length=4, max_length=20)


class CandidateCreate(BaseModel):
    place_id: str = Field(min_length=1, max_length=50, description="먼저 POST /places 로 저장한 장소")


class GroupMemberRead(BaseModel):
    user_id: str
    nickname: str
    role: str
    joined_at: datetime


class CandidateRead(BaseModel):
    id: str
    place: PlaceRead
    added_by_user_id: str
    added_by_nickname: str | None = None
    vote_count: int
    voted_by_me: bool


class GroupRead(BaseModel):
    id: str
    title: str | None = None
    invite_code: str
    status: str  # open | closed
    course_id: str | None = None
    course_group_id: str | None = None
    my_role: str
    members: list[GroupMemberRead]
    candidates: list[CandidateRead]


class GroupSummary(BaseModel):
    id: str
    title: str | None = None
    invite_code: str
    status: str
    my_role: str
    member_count: int
    candidate_count: int
    course_id: str | None = None


class GroupFinalizeRequest(BaseModel):
    """투표를 마감하고 코스를 만듭니다. (그룹 대표만 가능, 영업시간은 대표가 저장한 값을 사용)"""

    course_date: date
    start: StartPoint
    start_time: time
    title: str | None = Field(default=None, max_length=80)
    max_places: int = Field(default=5, ge=1, le=8, description="득표 상위 N곳만 코스에 넣습니다")
    default_stay_min: int | None = Field(default=None, ge=5, le=720, description="비우면 장소 유형별 추천 체류시간")
    stay_overrides: dict[str, int] = Field(default_factory=dict, description="장소별 체류시간(분)")

    @field_validator("course_date")
    @classmethod
    def not_past(cls, value: date) -> date:
        return ensure_not_past(value)

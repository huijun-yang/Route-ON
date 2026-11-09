from datetime import time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BusinessHoursCreate(BaseModel):
    """요청 본문. 장소 ID는 URL 경로에서, 사용자는 로그인 정보에서 가져옵니다."""

    weekday: int = Field(ge=0, le=6, description="0=월 ~ 6=일")
    # 심야 영업(예: 18:00~02:00)을 허용하기 위해 close_time > open_time 검증은 하지 않습니다.
    open_time: time
    close_time: time
    # 브레이크타임: 없으면 둘 다 비워둡니다.
    break_start: time | None = None
    break_end: time | None = None

    @model_validator(mode="after")
    def check_break_pair(self):
        if (self.break_start is None) != (self.break_end is None):
            raise ValueError("break_start 와 break_end 는 함께 입력하거나 둘 다 비워야 합니다")
        return self


class BusinessHoursRead(BusinessHoursCreate):
    model_config = ConfigDict(from_attributes=True)

    place_id: str

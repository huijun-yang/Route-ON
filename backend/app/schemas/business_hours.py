from datetime import time

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


class BusinessHoursBase(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0=월 ~ 6=일")
    # 심야 영업(예: 18:00~02:00)을 허용하므로 close_time > open_time 검증은 하지 않습니다.
    # open_time 과 close_time 이 같으면 24시간 영업으로 봅니다.
    open_time: time
    close_time: time
    # 브레이크타임: 없으면 둘 다 비워둡니다.
    break_start: time | None = None
    break_end: time | None = None


class BusinessHoursCreate(BusinessHoursBase):
    """요청 본문. 장소 ID는 URL 경로에서, 사용자는 로그인 정보에서 가져옵니다."""

    @model_validator(mode="after")
    def check_break(self):
        if (self.break_start is None) != (self.break_end is None):
            raise ValueError("break_start 와 break_end 는 함께 입력하거나 둘 다 비워야 합니다")
        if self.break_start is None:
            return self
        if self.break_start == self.break_end:
            raise ValueError("브레이크타임의 시작과 끝이 같을 수 없습니다")

        # 자정을 넘기는 경우까지 한 줄(분 단위, 1440=24시간)로 펴서 비교합니다.
        open_m, close_m = _minutes(self.open_time), _minutes(self.close_time)
        if close_m <= open_m:
            close_m += 1440
        start_m, end_m = _minutes(self.break_start), _minutes(self.break_end)
        if start_m < open_m:
            start_m += 1440
        if end_m <= start_m:
            end_m += 1440
        if not (open_m <= start_m < end_m <= close_m):
            raise ValueError("브레이크타임은 영업시간 안에 있어야 합니다")
        return self


class BusinessHoursRead(BusinessHoursBase):
    model_config = ConfigDict(from_attributes=True)

    place_id: str

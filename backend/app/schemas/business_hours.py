from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


class HoursFields(BaseModel):
    """영업시간 입력 공통 필드. 요일/날짜 키는 하위 클래스가 가집니다."""

    # 휴무일이면 is_closed=true 로 보내고 시간은 비워둡니다.
    is_closed: bool = False
    # 심야 영업(예: 18:00~02:00)을 허용하므로 close_time > open_time 검증은 하지 않습니다.
    # open_time 과 close_time 이 같으면 24시간 영업으로 봅니다.
    open_time: time | None = None
    close_time: time | None = None
    # 브레이크타임: 없으면 둘 다 비워둡니다.
    break_start: time | None = None
    break_end: time | None = None

    @model_validator(mode="after")
    def check_hours(self):
        if self.is_closed:
            if any(v is not None for v in (self.open_time, self.close_time, self.break_start, self.break_end)):
                raise ValueError("휴무일(is_closed=true)에는 영업시간/브레이크타임을 입력할 수 없습니다")
            return self
        if self.open_time is None or self.close_time is None:
            raise ValueError("open_time 과 close_time 은 휴무일이 아니면 필수입니다")
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


class BusinessHoursBase(HoursFields):
    weekday: int = Field(ge=0, le=6, description="0=월 ~ 6=일")


class BusinessHoursCreate(BusinessHoursBase):
    """요청 본문. 장소 ID는 URL 경로에서, 사용자는 로그인 정보에서 가져옵니다."""


class BusinessHoursRead(BusinessHoursBase):
    model_config = ConfigDict(from_attributes=True)

    place_id: str


class BusinessHoursExceptionCreate(HoursFields):
    """특정 날짜 하나에만 적용되는 영업시간 (임시휴무, 특별 영업시간). 요일별 값보다 우선합니다."""

    date: date


class BusinessHoursExceptionRead(HoursFields):
    model_config = ConfigDict(from_attributes=True)

    place_id: str
    date: date

"""DB 의 영업시간(datetime.time)을 optimizer 의 Stop 으로 바꾸는 도우미.

business_hours 테이블의 한 행(open_time, close_time, break_start, break_end)과
체류시간을 넘기면 됩니다. 입력 규칙은 schemas/business_hours.py 와 같습니다.
  - open_time == close_time  → 24시간 영업
  - close_time < open_time   → 자정을 넘기는 심야 영업
  - break_* 는 둘 다 있거나 둘 다 없어야 함
"""
from __future__ import annotations

from datetime import time

from app.optimizer.types import OptimizerInputError, Stop

DAY_MIN = 1440


def to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def make_stop(
    stop_id: str,
    open_time: time,
    close_time: time,
    stay_min: int,
    break_start: time | None = None,
    break_end: time | None = None,
) -> Stop:
    open_m = to_minutes(open_time)
    close_m = to_minutes(close_time)
    if open_m == close_m:
        # 24시간 영업: 하루 종일 + 다음날 새벽까지 방문 가능하게 넉넉히 잡습니다.
        open_m, close_m = 0, 2 * DAY_MIN
    elif close_m < open_m:
        close_m += DAY_MIN

    if (break_start is None) != (break_end is None):
        raise OptimizerInputError("break_start 와 break_end 는 함께 있거나 함께 없어야 합니다")

    bs = be = None
    if break_start is not None and break_end is not None:
        bs, be = to_minutes(break_start), to_minutes(break_end)
        if bs < open_m:  # 심야 영업에서 자정 이후에 있는 브레이크
            bs += DAY_MIN
        if be <= bs:
            be += DAY_MIN

    return Stop(
        id=stop_id,
        open_min=open_m,
        close_min=close_m,
        stay_min=stay_min,
        break_start_min=bs,
        break_end_min=be,
    )

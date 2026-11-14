"""optimizer 입출력 데이터 구조.

이 모듈은 DB, FastAPI, 외부 API 를 전혀 모르는 순수 데이터 정의입니다.
모든 시각은 '그날 0시부터 지난 분(minute)' 정수로 표현합니다. (예: 13:30 → 810)
영업시간이 자정을 넘기면 close_min 이 1440 을 넘을 수 있습니다. (예: 02:00 → 1560)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


class OptimizerInputError(ValueError):
    """optimizer 입력값이 잘못되었을 때 발생합니다. (행렬 크기 불일치, 음수 등)"""


@dataclass(frozen=True)
class Stop:
    """방문하고 싶은 장소 1곳.

    id:              장소 식별자 (kakao_place_id 등, 중복 불가)
    open_min:        영업 시작 시각(분)
    close_min:       영업 종료 시각(분). 자정을 넘기면 1440 이상
    stay_min:        체류시간(분)
    break_start_min: 브레이크타임 시작(분), 없으면 None
    break_end_min:   브레이크타임 종료(분), 없으면 None

    '방문 시작 시각 + 체류시간' 이 close_min 이하여야 하고,
    체류 구간이 브레이크타임과 겹치면 안 됩니다.
    """

    id: str
    open_min: int
    close_min: int
    stay_min: int
    break_start_min: int | None = None
    break_end_min: int | None = None


@dataclass(frozen=True)
class Problem:
    """최적화 문제 1건.

    start_min:  출발 시각(분)
    stops:      방문 후보 장소들
    travel_min: 이동시간 행렬(분, 정수). 크기는 (n+1) x (n+1)
                - 0 번 행/열 = 출발지
                - i+1 번 행/열 = stops[i]
                travel_min[a][b] = a 에서 b 로 가는 데 걸리는 시간 (비대칭 가능)
    cost:       (선택) 목적함수용 비용 행렬. 같은 크기의 정수 행렬.
                없으면 travel_min 을 비용으로 씁니다.
                우선순위 비교(이동시간/도보량/교통비)는 여기에 가중합을 넣어 구현합니다.
                예) cost[a][b] = w1*이동시간 + w2*도보거리(m)/10 + w3*요금/100
    """

    start_min: int
    stops: list[Stop]
    travel_min: list[list[int]]
    cost: list[list[int]] | None = None


@dataclass(frozen=True)
class Visit:
    """확정된 방문 1건.

    arrival_min:   이전 장소에서 바로 출발했을 때의 도착 시각
    start_min:     실제 방문(체류) 시작 시각. 영업 시작 전이면 문 열 때까지 기다린 시각
    departure_min: 체류를 마치고 떠나는 시각 (= start_min + stay_min)
    wait_min:      start_min - arrival_min (기다리거나 출발을 늦춰도 되는 여유 시간)
    travel_min:    이전 장소(또는 출발지)에서 여기까지의 이동시간
    """

    stop_id: str
    arrival_min: int
    start_min: int
    departure_min: int
    wait_min: int
    travel_min: int


ExcludeReason = Literal[
    "WINDOW_TOO_SHORT",  # 영업시간(브레이크 제외)이 체류시간보다 짧아 애초에 방문 불가
    "ALREADY_CLOSED",  # 출발 시각 이전에 이미 영업이 끝남 (재계획 때 자주 발생)
    "UNREACHABLE_IN_TIME",  # 이동시간/다른 장소 일정 때문에 영업시간 안에 갈 수 없음
]


@dataclass(frozen=True)
class Excluded:
    stop_id: str
    reason: ExcludeReason


@dataclass(frozen=True)
class Result:
    """최적화 결과.

    status:
      "OK"          모든 장소를 방문하는 코스를 찾음
      "PARTIAL"     일부 장소는 제외해야 함 (excluded 참고, 제외 추천)
      "NO_FEASIBLE" 방문 가능한 장소가 하나도 없음
    visits:            방문 순서대로 정렬된 방문 목록
    excluded:          제외를 추천하는 장소와 사유
    total_travel_min:  총 이동시간(분)
    end_min:           마지막 장소를 떠나는 시각 (방문이 없으면 start_min)
    """

    status: Literal["OK", "PARTIAL", "NO_FEASIBLE"]
    visits: list[Visit]
    excluded: list[Excluded]
    total_travel_min: int
    end_min: int

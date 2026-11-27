"""optimizer 단위 테스트. DB/외부 API 없이 돌아갑니다.  (backend 폴더에서 `pytest`)"""
from datetime import time

import pytest

from app.optimizer import (
    OptimizerInputError,
    Problem,
    Stop,
    make_stop,
    solve,
    to_minutes,
)

H = 60


def t(hour: int, minute: int = 0) -> int:
    return hour * 60 + minute


def uniform_matrix(n: int, minutes: int) -> list[list[int]]:
    """(n+1)x(n+1) 행렬: 자기 자신은 0, 나머지는 모두 minutes."""
    return [[0 if i == j else minutes for j in range(n + 1)] for i in range(n + 1)]


def assert_schedule_valid(problem: Problem, result) -> None:
    """결과의 모든 방문이 영업시간/브레이크/이동시간 규칙을 지키는지 검사."""
    by_id = {s.id: s for s in problem.stops}
    idx = {s.id: i + 1 for i, s in enumerate(problem.stops)}
    prev_node, prev_dep = 0, problem.start_min
    for v in result.visits:
        s = by_id[v.stop_id]
        assert v.arrival_min == prev_dep + problem.travel_min[prev_node][idx[v.stop_id]]
        assert v.start_min >= v.arrival_min
        assert v.start_min >= s.open_min
        assert v.departure_min == v.start_min + s.stay_min
        assert v.departure_min <= s.close_min
        if s.break_start_min is not None:
            # 체류 구간이 브레이크와 겹치면 안 됨
            assert v.departure_min <= s.break_start_min or v.start_min >= s.break_end_min
        prev_node, prev_dep = idx[v.stop_id], v.departure_min


# ---------------------------------------------------------------- 정상 동작
def test_break_time_forces_order():
    """14:00 출발. B(맛집)는 15~17시 브레이크, C(전시)는 18시 마감 → C 먼저, B 나중이어야 함."""
    b = Stop("B", t(11), t(21), 60, t(15), t(17))
    c = Stop("C", t(10), t(18), 120)
    problem = Problem(start_min=t(14), stops=[b, c], travel_min=uniform_matrix(2, 20))

    result = solve(problem, time_limit_sec=1)

    assert result.status == "OK"
    assert [v.stop_id for v in result.visits] == ["C", "B"]
    b_visit = result.visits[1]
    assert b_visit.start_min == t(17)  # 브레이크가 끝나는 17:00 까지 기다림
    assert b_visit.wait_min > 0
    assert_schedule_valid(problem, result)


def test_all_three_places_scheduled_validly():
    a = Stop("A", t(10), t(22), 60)
    b = Stop("B", t(11), t(21), 60, t(15), t(17))
    c = Stop("C", t(10), t(18), 120)
    problem = Problem(start_min=t(13), stops=[a, b, c], travel_min=uniform_matrix(3, 20))

    result = solve(problem, time_limit_sec=1)

    assert result.status == "OK"
    assert {v.stop_id for v in result.visits} == {"A", "B", "C"}
    assert_schedule_valid(problem, result)


def test_waits_until_opening():
    """영업 시작 전에 도착하면 문 열 때까지 기다림."""
    a = Stop("A", t(11), t(20), 60)
    problem = Problem(start_min=t(10), stops=[a], travel_min=uniform_matrix(1, 10))

    result = solve(problem, time_limit_sec=1)

    v = result.visits[0]
    assert v.arrival_min == t(10, 10)
    assert v.start_min == t(11)
    assert v.wait_min == 50


def test_asymmetric_travel_times_are_used():
    """이동시간이 비대칭이어도 출발→도착 방향대로 계산."""
    a = Stop("A", t(9), t(23), 30)
    b = Stop("B", t(9), t(23), 30)
    travel = [
        [0, 5, 50],  # 출발지 → A 5분, → B 50분
        [5, 0, 5],
        [50, 5, 0],
    ]
    problem = Problem(start_min=t(10), stops=[a, b], travel_min=travel)

    result = solve(problem, time_limit_sec=1)

    assert [v.stop_id for v in result.visits] == ["A", "B"]
    assert result.total_travel_min == 10


def test_custom_cost_changes_order():
    """시간은 같아도 cost 행렬(예: 도보거리 우선)에 따라 순서가 달라짐."""
    a = Stop("A", t(9), t(23), 30)
    b = Stop("B", t(9), t(23), 30)
    travel = uniform_matrix(2, 10)
    cost = [
        [0, 100, 1],  # 출발지 → A 는 비싸고 → B 는 쌈
        [100, 0, 1],
        [1, 1, 0],
    ]
    problem = Problem(start_min=t(10), stops=[a, b], travel_min=travel, cost=cost)

    result = solve(problem, time_limit_sec=1)

    assert [v.stop_id for v in result.visits] == ["B", "A"]


def test_overnight_business_hours():
    """18:00~02:00 영업하는 바에 23:00 방문 가능."""
    bar = make_stop("bar", time(18, 0), time(2, 0), 60)
    problem = Problem(start_min=t(22), stops=[bar], travel_min=uniform_matrix(1, 60))

    result = solve(problem, time_limit_sec=1)

    assert result.status == "OK"
    assert result.visits[0].start_min == t(23)


# ---------------------------------------------------------------- 제외 추천
def test_unreachable_stop_is_excluded_but_others_scheduled():
    """B 는 10:30 마감인데 출발지에서 1시간 걸려 갈 수 없음 → B 만 제외."""
    a = Stop("A", t(9), t(22), 60)
    b = Stop("B", t(9), t(10, 30), 30)
    travel = [
        [0, 10, 60],
        [10, 0, 60],
        [60, 60, 0],
    ]
    problem = Problem(start_min=t(10), stops=[a, b], travel_min=travel)

    result = solve(problem, time_limit_sec=1)

    assert result.status == "PARTIAL"
    assert [v.stop_id for v in result.visits] == ["A"]
    assert [(e.stop_id, e.reason) for e in result.excluded] == [("B", "UNREACHABLE_IN_TIME")]


def test_already_closed_before_start():
    a = Stop("A", t(9), t(22), 60)
    b = Stop("B", t(9), t(12), 30)
    problem = Problem(start_min=t(13), stops=[a, b], travel_min=uniform_matrix(2, 10))

    result = solve(problem, time_limit_sec=1)

    assert result.status == "PARTIAL"
    assert [(e.stop_id, e.reason) for e in result.excluded] == [("B", "ALREADY_CLOSED")]


def test_window_shorter_than_stay():
    a = Stop("A", t(10), t(11), 120)  # 1시간 영업인데 2시간 체류
    problem = Problem(start_min=t(9), stops=[a], travel_min=uniform_matrix(1, 5))

    result = solve(problem, time_limit_sec=1)

    assert result.status == "NO_FEASIBLE"
    assert result.visits == []
    assert [(e.stop_id, e.reason) for e in result.excluded] == [("A", "WINDOW_TOO_SHORT")]
    assert result.end_min == t(9)


def test_stay_that_only_fits_inside_break_is_excluded():
    """영업 12~14시 전체가 브레이크와 겹치는 경우 → 방문 불가."""
    a = Stop("A", t(12), t(14), 60, t(12), t(14))
    problem = Problem(start_min=t(9), stops=[a], travel_min=uniform_matrix(1, 5))

    result = solve(problem, time_limit_sec=1)

    assert result.status == "NO_FEASIBLE"
    assert result.excluded[0].reason == "WINDOW_TOO_SHORT"


def test_empty_stops():
    problem = Problem(start_min=t(9), stops=[], travel_min=[[0]])
    result = solve(problem, time_limit_sec=1)
    assert result.status == "NO_FEASIBLE"
    assert result.visits == [] and result.excluded == []


# ---------------------------------------------------------------- 재계획(같은 엔진 재사용)
def test_replan_from_current_position_drops_closed_place():
    """코스 도중 15:30 에 현재 위치에서 남은 장소만 다시 계산."""
    remaining_ok = Stop("D", t(10), t(22), 60)
    remaining_closed = Stop("E", t(10), t(15), 30)  # 15시에 이미 마감
    # 0 = 현재 위치
    problem = Problem(
        start_min=t(15, 30),
        stops=[remaining_ok, remaining_closed],
        travel_min=uniform_matrix(2, 15),
    )

    result = solve(problem, time_limit_sec=1)

    assert [v.stop_id for v in result.visits] == ["D"]
    assert result.excluded[0].stop_id == "E"


# ---------------------------------------------------------------- 입력 검증
def test_rejects_wrong_matrix_shape():
    a = Stop("A", t(9), t(22), 30)
    with pytest.raises(OptimizerInputError):
        solve(Problem(t(10), [a], [[0, 1], [1]]), time_limit_sec=1)


def test_rejects_negative_travel_time():
    a = Stop("A", t(9), t(22), 30)
    with pytest.raises(OptimizerInputError):
        solve(Problem(t(10), [a], [[0, -1], [1, 0]]), time_limit_sec=1)


def test_rejects_duplicate_ids():
    a1 = Stop("A", t(9), t(22), 30)
    a2 = Stop("A", t(9), t(22), 30)
    with pytest.raises(OptimizerInputError):
        solve(Problem(t(10), [a1, a2], uniform_matrix(2, 5)), time_limit_sec=1)


# ---------------------------------------------------------------- windows.make_stop
def test_make_stop_normal():
    s = make_stop("x", time(11, 0), time(21, 0), 60, time(15, 0), time(17, 0))
    assert (s.open_min, s.close_min) == (t(11), t(21))
    assert (s.break_start_min, s.break_end_min) == (t(15), t(17))


def test_make_stop_overnight_and_24h():
    night = make_stop("n", time(18, 0), time(2, 0), 60)
    assert (night.open_min, night.close_min) == (t(18), t(26))

    always = make_stop("a", time(0, 0), time(0, 0), 60)
    assert always.open_min == 0 and always.close_min == 2 * 24 * H


def test_make_stop_overnight_break_after_midnight():
    s = make_stop("n", time(18, 0), time(3, 0), 60, time(0, 30), time(1, 0))
    assert (s.break_start_min, s.break_end_min) == (t(24, 30), t(25))


def test_make_stop_requires_both_break_fields():
    with pytest.raises(OptimizerInputError):
        make_stop("x", time(9), time(18), 30, break_start=time(12), break_end=None)


def test_to_minutes():
    assert to_minutes(time(13, 30)) == 810

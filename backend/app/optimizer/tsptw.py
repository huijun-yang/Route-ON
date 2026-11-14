"""시간창 제약 TSP(TSPTW) 풀이 — Google OR-Tools Routing 사용.

핵심 아이디어
  - 출발지에서 시작해 마지막 장소에서 끝나는 '오픈 경로'입니다. (돌아오지 않음)
    → 비용 0 인 더미 종료 노드를 하나 두어 구현합니다.
  - 노드의 누적 시간(cumul) = 그 장소의 '방문 시작 시각'.
    전이 시간 = 이동시간 + 출발 장소의 체류시간.
  - 영업시간 → 방문 시작 가능 구간 [open, close - 체류].
    브레이크타임은 '체류 구간이 브레이크와 겹치는 시작 시각'을 RemoveInterval 로 제거합니다.
  - 모든 장소에 큰 페널티가 붙은 Disjunction 을 걸어, 못 가는 장소는 경로에서 빠지게 합니다.
    (빠진 장소 = 제외 추천)
  - 목적함수 = 비용 행렬 합 + span_cost_coefficient × 전체 소요시간.

이 모듈은 DB/FastAPI 를 import 하지 않습니다. solve(problem) 순수 함수만 노출합니다.
"""
from __future__ import annotations

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.optimizer.types import (
    Excluded,
    OptimizerInputError,
    Problem,
    Result,
    Stop,
    Visit,
)

Interval = tuple[int, int]  # 방문 '시작' 가능 구간 [a, b] (양끝 포함)


def _validate(problem: Problem) -> None:
    n = len(problem.stops)
    size = n + 1

    ids = [s.id for s in problem.stops]
    if len(set(ids)) != len(ids):
        raise OptimizerInputError("stops 의 id 가 중복되었습니다")
    if problem.start_min < 0:
        raise OptimizerInputError("start_min 은 0 이상이어야 합니다")

    def check_matrix(name: str, matrix: list[list[int]]) -> None:
        if len(matrix) != size or any(len(row) != size for row in matrix):
            raise OptimizerInputError(
                f"{name} 는 (n+1) x (n+1) 행렬이어야 합니다 (n={n}, 받은 행 수={len(matrix)})"
            )
        for row in matrix:
            for v in row:
                if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    raise OptimizerInputError(f"{name} 의 값은 0 이상의 정수(분)여야 합니다")

    check_matrix("travel_min", problem.travel_min)
    if problem.cost is not None:
        check_matrix("cost", problem.cost)

    for s in problem.stops:
        if s.stay_min < 0:
            raise OptimizerInputError(f"{s.id}: stay_min 은 0 이상이어야 합니다")
        if s.close_min <= s.open_min:
            raise OptimizerInputError(f"{s.id}: close_min 은 open_min 보다 커야 합니다")
        if (s.break_start_min is None) != (s.break_end_min is None):
            raise OptimizerInputError(f"{s.id}: 브레이크 시작/종료는 함께 있어야 합니다")
        if s.break_start_min is not None and s.break_end_min is not None:
            if s.break_end_min <= s.break_start_min:
                raise OptimizerInputError(f"{s.id}: 브레이크 종료가 시작보다 늦어야 합니다")


def _allowed_start_intervals(stop: Stop, earliest: int = 0) -> list[Interval]:
    """방문을 '시작'할 수 있는 시각 구간들. earliest 이전은 잘라냅니다."""
    lo = max(stop.open_min, earliest)
    hi = stop.close_min - stop.stay_min  # 체류가 영업 종료 전에 끝나야 함
    if lo > hi:
        return []
    intervals = [(lo, hi)]

    if stop.break_start_min is not None and stop.break_end_min is not None:
        # 체류 구간 [t, t+stay) 가 브레이크 [bs, be) 와 겹치는 t:  bs - stay < t < be
        f_lo = stop.break_start_min - stop.stay_min + 1
        f_hi = stop.break_end_min - 1
        if f_lo <= f_hi:
            cut: list[Interval] = []
            for a, b in intervals:
                if b < f_lo or a > f_hi:
                    cut.append((a, b))
                    continue
                if a < f_lo:
                    cut.append((a, f_lo - 1))
                if b > f_hi:
                    cut.append((f_hi + 1, b))
            intervals = cut
    return intervals


def solve(
    problem: Problem,
    *,
    time_limit_sec: float = 2.0,
    drop_penalty: int = 1_000_000,
    span_cost_coefficient: int = 1,
) -> Result:
    """최적 방문 순서를 계산합니다.

    time_limit_sec:        탐색 제한 시간. 장소가 적어도 이 시간 동안 개선을 시도합니다.
    drop_penalty:          장소를 제외할 때의 페널티. 정상적인 경로 비용보다 훨씬 커야
                           '가능하면 모두 방문'이 됩니다. 일부러 낮추면 비싼 장소를 제외하게 됩니다.
    span_cost_coefficient: 전체 소요시간(분)에 곱하는 가중치. 0 이면 소요시간은 무시합니다.
    """
    _validate(problem)
    stops = problem.stops
    n = len(stops)

    # 1) 사전 필터: 어떻게 해도 방문할 수 없는 장소는 모델에 넣지 않습니다.
    #    (빈 시간창을 solver 에 주면 모델이 깨질 수 있습니다.)
    excluded: list[Excluded] = []
    usable: list[tuple[int, Stop, list[Interval]]] = []  # (stops 인덱스, Stop, 시작 가능 구간)
    for i, s in enumerate(stops):
        if not _allowed_start_intervals(s):
            excluded.append(Excluded(s.id, "WINDOW_TOO_SHORT"))
            continue
        intervals = _allowed_start_intervals(s, earliest=problem.start_min)
        if not intervals:
            excluded.append(Excluded(s.id, "ALREADY_CLOSED"))
            continue
        usable.append((i, s, intervals))

    if not usable:
        return Result("NO_FEASIBLE", [], excluded, 0, problem.start_min)

    # 2) 모델 노드: 0 = 출발지, 1..m = usable 장소, m+1 = 더미 종료 노드
    m = len(usable)
    end_node = m + 1
    orig = [0] + [i + 1 for i, _, _ in usable]  # 모델 노드 → problem 행렬 인덱스
    stay = [0] + [s.stay_min for _, s, _ in usable]
    travel = problem.travel_min
    cost = problem.cost if problem.cost is not None else problem.travel_min

    horizon = max([problem.start_min] + [s.close_min for _, s, _ in usable]) + 24 * 60

    manager = pywrapcp.RoutingIndexManager(m + 2, 1, [0], [end_node])
    routing = pywrapcp.RoutingModel(manager)

    def transit_cb(from_index: int, to_index: int) -> int:
        f, t = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        if f == end_node:
            return 0
        if t == end_node:
            return stay[f]
        return travel[orig[f]][orig[t]] + stay[f]

    def cost_cb(from_index: int, to_index: int) -> int:
        f, t = manager.IndexToNode(from_index), manager.IndexToNode(to_index)
        if f == end_node or t == end_node:
            return 0
        return cost[orig[f]][orig[t]]

    transit_idx = routing.RegisterTransitCallback(transit_cb)
    cost_idx = routing.RegisterTransitCallback(cost_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(cost_idx)

    # 3) 시간 차원: 대기(slack) 허용, 출발 시각 고정
    routing.AddDimension(transit_idx, horizon, horizon, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    time_dim.SetSpanCostCoefficientForAllVehicles(span_cost_coefficient)
    time_dim.CumulVar(routing.Start(0)).SetRange(problem.start_min, problem.start_min)

    # 4) 시간창 + 브레이크타임 + 제외 가능(Disjunction)
    for node, (_, _, intervals) in enumerate(usable, start=1):
        var = time_dim.CumulVar(manager.NodeToIndex(node))
        var.SetRange(intervals[0][0], intervals[-1][1])
        for (_, prev_end), (next_start, _) in zip(intervals, intervals[1:]):
            var.RemoveInterval(prev_end + 1, next_start - 1)
        routing.AddDisjunction([manager.NodeToIndex(node)], drop_penalty)

    # 5) 탐색
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.FromMilliseconds(max(1, int(time_limit_sec * 1000)))

    assignment = routing.SolveWithParameters(params)
    if assignment is None:
        # 모든 장소를 제외하는 해는 항상 존재하므로 정상이라면 여기 오지 않습니다.
        raise RuntimeError("OR-Tools 가 해를 찾지 못했습니다 (입력값을 확인하세요)")

    # 6) 결과 추출
    visits: list[Visit] = []
    total_travel = 0
    prev_orig = 0
    prev_departure = problem.start_min

    index = assignment.Value(routing.NextVar(routing.Start(0)))
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        cur_orig = orig[node]
        stop = stops[cur_orig - 1]

        start = assignment.Value(time_dim.CumulVar(index))
        move = travel[prev_orig][cur_orig]
        arrival = prev_departure + move
        departure = start + stop.stay_min

        visits.append(
            Visit(
                stop_id=stop.id,
                arrival_min=arrival,
                start_min=start,
                departure_min=departure,
                wait_min=start - arrival,
                travel_min=move,
            )
        )
        total_travel += move
        prev_orig, prev_departure = cur_orig, departure
        index = assignment.Value(routing.NextVar(index))

    visited_ids = {v.stop_id for v in visits}
    for _, s, _ in usable:
        if s.id not in visited_ids:
            excluded.append(Excluded(s.id, "UNREACHABLE_IN_TIME"))

    if not visits:
        status = "NO_FEASIBLE"
    elif excluded:
        status = "PARTIAL"
    else:
        status = "OK"

    return Result(
        status=status,
        visits=visits,
        excluded=excluded,
        total_travel_min=total_travel,
        end_min=prev_departure,
    )

"""장소 목록 → 우선순위별 코스 3개(시간/도보/비용)를 계산해 저장합니다.

DB(장소·영업시간) → 영업시간 확정 → 이동시간 행렬(travel.py) → optimizer.solve → Course/CourseStop 저장
의 순서로 흐르며, 한 번의 요청에서 같은 group_id 로 묶인 코스 3개를 만듭니다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import BusinessHours, BusinessHoursException, Course, CourseStop, Place
from app.models.base import gen_uuid
from app.optimizer import Problem, make_stop, solve
from app.optimizer.types import OptimizerInputError, Result
from app.schemas.course import HoursOverride, ReplanRequest, StopInput
from app.services.stay_time import recommend_stay
from app.services.travel import Leg, Point, TravelService

PRIORITIES = ("time", "walk", "cost")
PRIORITY_LABEL = {"time": "최단 시간", "walk": "최소 도보", "cost": "최저 비용"}

# 우선순위별 목적함수 가중치 (정수 분 단위로 환산)
#   time: 이동시간
#   walk: 도보시간 x3 + 이동시간   (많이 걷는 구간에 큰 벌점)
#   cost: 요금(원)/10 + 이동시간   (150원 = 15점, 요금 차이가 이동시간보다 크게 반영됨)
WALK_WEIGHT = 3
FARE_DIVISOR = 10
SPAN_COEFFICIENT = {"time": 1, "walk": 0, "cost": 0}


class PlanError(Exception):
    def __init__(self, status_code: int, detail):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


@dataclass
class PlanStopSpec:
    place: Place
    stay_min: int
    estimated_cost: int
    hours: dict  # {"open","close","break_start","break_end","source"}


@dataclass
class PlanOutcome:
    group_id: str
    courses: list[Course]
    warnings: list[str]


def _hhmm(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def hours_snapshot(row_or_override, source: str) -> dict:
    if row_or_override.is_closed:
        return {"closed": True, "open": None, "close": None, "break_start": None, "break_end": None, "source": source}
    return {
        "closed": False,
        "open": _hhmm(row_or_override.open_time),
        "close": _hhmm(row_or_override.close_time),
        "break_start": _hhmm(row_or_override.break_start) if row_or_override.break_start else None,
        "break_end": _hhmm(row_or_override.break_end) if row_or_override.break_end else None,
        "source": source,
    }


ASSUMED_24H = {"closed": False, "open": "00:00", "close": "00:00", "break_start": None, "break_end": None, "source": "assumed"}


def resolve_hours(
    db: Session, hours_user_id: str, place_id: str, course_date: date, override: HoursOverride | None
) -> dict:
    """영업시간 우선순위: 요청에 직접 넣은 값 > 날짜별 예외(임시휴무 등) > 요일별 저장값 > 24시간 영업 가정."""
    if override is not None:
        return hours_snapshot(override, "inline")
    exc = db.get(BusinessHoursException, (hours_user_id, place_id, course_date))
    if exc is not None:
        return hours_snapshot(exc, "exception")
    weekday = course_date.weekday()
    row = db.get(BusinessHours, (hours_user_id, place_id, weekday))
    if row is not None:
        return hours_snapshot(row, "saved")
    return dict(ASSUMED_24H)


def build_specs_from_inputs(
    db: Session, *, hours_user_id: str, course_date: date, inputs: list[StopInput]
) -> list[PlanStopSpec]:
    ids = [i.place_id for i in inputs]
    places = {p.kakao_place_id: p for p in db.query(Place).filter(Place.kakao_place_id.in_(ids)).all()}
    missing = [pid for pid in ids if pid not in places]
    if missing:
        raise PlanError(404, {"message": "저장되지 않은 장소가 있습니다. 먼저 POST /places 로 저장하세요", "missing_place_ids": missing})
    return [
        PlanStopSpec(
            place=places[i.place_id],
            stay_min=i.stay_min if i.stay_min is not None else recommend_stay(places[i.place_id].category),
            estimated_cost=i.estimated_cost,
            hours=resolve_hours(db, hours_user_id, i.place_id, course_date, i.hours),
        )
        for i in inputs
    ]


def _excluded_entry(spec: PlanStopSpec, reason: str) -> dict:
    """제외된 장소 기록. 재계획 때 같은 조건으로 다시 시도할 수 있도록 체류시간/영업시간도 함께 남깁니다."""
    return {
        "place_id": spec.place.kakao_place_id,
        "name": spec.place.name,
        "reason": reason,
        "stay_min": spec.stay_min,
        "estimated_cost": spec.estimated_cost,
        "hours": spec.hours,
    }


def _cost_matrix(priority: str, legs: list[list[Leg]]) -> list[list[int]]:
    n = len(legs)
    out = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            leg = legs[i][j]
            if priority == "time":
                out[i][j] = leg.travel_min
            elif priority == "walk":
                out[i][j] = WALK_WEIGHT * leg.walk_min + leg.travel_min
            else:
                out[i][j] = leg.fare // FARE_DIVISOR + leg.travel_min
    return out


def _time_limit(n: int) -> float:
    # 장소가 적으면 짧게 끝내서 응답을 빠르게 합니다.
    if n <= 3:
        return 0.3
    if n <= 6:
        return 0.8
    return 1.5


def _stop_time(s: str) -> time:
    return time.fromisoformat(s)


def plan_courses(
    db: Session,
    *,
    owner_id: str,
    title: str,
    course_date: date,
    start: Point,
    start_min: int,
    specs: list[PlanStopSpec],
    travel: TravelService,
    update_group_id: str | None = None,
) -> PlanOutcome:
    """코스 3개를 계산해 저장합니다.

    update_group_id 가 있으면 새로 만들지 않고, 그 묶음의 기존 코스(같은 우선순위)를 계산 결과로 덮어씁니다.
    (id, 공유 링크, 제목, 선택된 버전은 그대로 유지됩니다.)
    """
    if not specs:
        raise PlanError(422, "방문할 장소가 없습니다")

    # 그날 휴무인 장소는 최적화에 넣지 않고 곧바로 제외합니다.
    closed_specs = [s for s in specs if s.hours.get("closed")]
    specs = [s for s in specs if not s.hours.get("closed")]
    closed_excluded = [_excluded_entry(s, "CLOSED_ON_DAY") for s in closed_specs]
    if not specs:
        raise PlanError(
            422,
            {"message": "선택한 장소가 모두 그날 휴무입니다", "excluded": closed_excluded},
        )

    points = [start] + [Point(s.place.lat, s.place.lng) for s in specs]
    depart = datetime.combine(course_date, time(start_min // 60 % 24, start_min % 60))
    legs = travel.leg_matrix(points, depart)
    travel_min = [[leg.travel_min for leg in row] for row in legs]

    try:
        stops = [
            make_stop(
                s.place.kakao_place_id,
                _stop_time(s.hours["open"]),
                _stop_time(s.hours["close"]),
                s.stay_min,
                _stop_time(s.hours["break_start"]) if s.hours.get("break_start") else None,
                _stop_time(s.hours["break_end"]) if s.hours.get("break_end") else None,
            )
            for s in specs
        ]
    except OptimizerInputError as exc:
        raise PlanError(422, str(exc)) from exc

    results: dict[str, Result] = {}
    for priority in PRIORITIES:
        problem = Problem(
            start_min=start_min,
            stops=stops,
            travel_min=travel_min,
            cost=_cost_matrix(priority, legs),
        )
        try:
            results[priority] = solve(
                problem,
                time_limit_sec=_time_limit(len(specs)),
                span_cost_coefficient=SPAN_COEFFICIENT[priority],
            )
        except OptimizerInputError as exc:
            raise PlanError(422, str(exc)) from exc

    spec_by_id = {s.place.kakao_place_id: s for s in specs}
    idx_by_id = {s.place.kakao_place_id: i + 1 for i, s in enumerate(specs)}

    if all(r.status == "NO_FEASIBLE" for r in results.values()):
        any_result = results["time"]
        raise PlanError(
            422,
            {
                "message": "영업시간/이동시간 때문에 방문할 수 있는 장소가 하나도 없습니다",
                "excluded": [_excluded_entry(spec_by_id[e.stop_id], e.reason) for e in any_result.excluded]
                + closed_excluded,
            },
        )

    group_id = gen_uuid()
    courses: list[Course] = []
    first_with_visits = next((p for p in PRIORITIES if results[p].visits), None)

    for priority in PRIORITIES:
        res = results[priority]
        course = Course(
            owner_user_id=owner_id,
            group_id=group_id,
            priority_type=priority,
            is_active=(priority == first_with_visits),
            title=f"{title} · {PRIORITY_LABEL[priority]}"[:100],
            course_date=course_date,
            status="PARTIAL" if (closed_excluded and res.status == "OK") else res.status,
            start_lat=start.lat,
            start_lng=start.lng,
            start_min=start_min,
            end_min=res.end_min,
            total_travel_min=res.total_travel_min,
            excluded=[_excluded_entry(spec_by_id[e.stop_id], e.reason) for e in res.excluded] + closed_excluded,
        )
        prev_idx = 0
        total_walk_min = total_walk_m = total_fare = 0
        for order, v in enumerate(res.visits, start=1):
            cur_idx = idx_by_id[v.stop_id]
            leg = legs[prev_idx][cur_idx]
            spec = spec_by_id[v.stop_id]
            total_walk_min += leg.walk_min
            total_walk_m += leg.walk_m
            total_fare += leg.fare
            course.stops.append(
                CourseStop(
                    place_id=v.stop_id,
                    visit_order=order,
                    arrival_min=v.arrival_min,
                    start_min=v.start_min,
                    departure_min=v.departure_min,
                    stay_duration=spec.stay_min,
                    estimated_cost=spec.estimated_cost,
                    travel_min=v.travel_min,
                    wait_min=v.wait_min,
                    walk_min=leg.walk_min,
                    walk_m=leg.walk_m,
                    fare=leg.fare,
                    travel_source=leg.source,
                    hours=spec.hours,
                )
            )
            prev_idx = cur_idx
        course.total_walk_min = total_walk_min
        course.total_walk_m = total_walk_m
        course.total_fare = total_fare
        courses.append(course)

    warnings: list[str] = []
    for s in closed_specs:
        warnings.append(f"'{s.place.name}' 은(는) {course_date.isoformat()} 휴무라 코스에서 제외했습니다")
    for s in specs:
        if s.hours["source"] == "assumed":
            warnings.append(f"'{s.place.name}' 영업시간이 없어 24시간 영업으로 가정했습니다")
    if any(leg.source == "estimate" for row in legs for leg in row):
        reasons = getattr(travel, "issues", [])
        detail = f" ({'; '.join(reasons)})" if reasons else " (Tmap 조회 불가)"
        warnings.append(f"일부 구간의 이동시간은 직선거리 기반 추정값입니다{detail}")

    if update_group_id is not None:
        courses = _overwrite_group(db, update_group_id, courses)
        group_id = update_group_id
    else:
        db.add_all(courses)
    db.commit()
    for c in courses:
        db.refresh(c)
    return PlanOutcome(group_id=group_id, courses=courses, warnings=warnings)


def _overwrite_group(db: Session, group_id: str, fresh: list[Course]) -> list[Course]:
    """새로 계산한 코스(저장 전)의 내용을 같은 묶음의 기존 코스에 옮겨 덮어씁니다. 반환: 저장될 코스 목록."""
    existing = {
        c.priority_type: c
        for c in db.scalars(
            select(Course).options(selectinload(Course.stops)).where(Course.group_id == group_id)
        ).all()
    }
    result: list[Course] = []
    for new in fresh:
        old = existing.get(new.priority_type)
        if old is None:  # 기존에 없던 버전이면 같은 묶음으로 새로 추가
            new.group_id = group_id
            db.add(new)
            result.append(new)
            continue
        for field in (
            "status", "start_lat", "start_lng", "start_min", "end_min", "total_travel_min",
            "total_walk_min", "total_walk_m", "total_fare", "excluded",
        ):
            setattr(old, field, getattr(new, field))
        # 새 방문 기록을 값만 복사해 붙입니다. (저장 전 객체를 그대로 옮기면 SQLAlchemy 가 임시 코스까지 함께 저장해 버립니다)
        # 이전 방문 기록은 delete-orphan 으로 삭제됩니다.
        columns = [c.name for c in CourseStop.__table__.columns if c.name not in ("id", "course_id")]
        old.stops = [CourseStop(**{name: getattr(stop, name) for name in columns}) for stop in new.stops]
        result.append(old)
    return result


def replan_course(
    db: Session,
    *,
    course: Course,
    owner_id: str,
    req: ReplanRequest,
    travel: TravelService,
    in_place: bool = False,
) -> PlanOutcome:
    """남은 장소만 현재 위치·시각 기준으로 다시 계산합니다.

    in_place=True 면 기존 코스 묶음을 덮어써서 갱신합니다. (히스토리에 새 항목이 생기지 않음)
    False 면 원래 코스는 그대로 두고 새 코스 3개를 만듭니다. (코스 주인이 아닌 그룹 멤버가 재계획할 때)
    """
    visited = set(req.visited_place_ids)
    remaining = [s for s in course.stops if s.place_id not in visited]
    # 이전 계산에서 제외됐던 장소도 다시 시도합니다. (현재 위치·시각이 바뀌면 갈 수 있게 될 수 있음)
    retry = [e for e in (course.excluded or []) if e.get("place_id") not in visited]
    if not remaining and not retry:
        raise PlanError(422, "남은 장소가 없습니다")

    specs: list[PlanStopSpec] = []
    for s in remaining:
        base = s.stay_duration or recommend_stay(s.place.category)
        stay = max(5, base + req.stay_adjustments.get(s.place_id, 0))
        specs.append(
            PlanStopSpec(
                place=s.place,
                stay_min=stay,
                estimated_cost=s.estimated_cost,
                hours=dict(s.hours) if s.hours else dict(ASSUMED_24H),
            )
        )

    in_course = {s.place_id for s in remaining}
    for e in retry:
        place = db.get(Place, e.get("place_id"))
        if place is None or place.kakao_place_id in in_course:
            continue
        stay = max(5, (e.get("stay_min") or recommend_stay(place.category)) + req.stay_adjustments.get(place.kakao_place_id, 0))
        specs.append(
            PlanStopSpec(
                place=place,
                stay_min=stay,
                estimated_cost=e.get("estimated_cost", 0),
                hours=dict(e["hours"]) if e.get("hours") else dict(ASSUMED_24H),
            )
        )

    base_title = course.title.split(" · ")[0][:80]
    return plan_courses(
        db,
        owner_id=owner_id,
        title=f"{base_title} (재계획)",
        course_date=course.course_date,
        start=Point(req.current_lat, req.current_lng),
        start_min=req.current_time.hour * 60 + req.current_time.minute,
        specs=specs,
        travel=travel,
        update_group_id=course.group_id if in_place else None,
    )

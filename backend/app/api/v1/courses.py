from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Course, CourseStop, GroupSession, User
from app.schemas.course import (
    CourseCreateRequest,
    CoursePlanResponse,
    CourseRead,
    CourseSummary,
    CourseUpdate,
    ReplanRequest,
)
from app.services.access import can_view_course
from app.services.course_planner import (
    PlanError,
    PlanOutcome,
    build_specs_from_inputs,
    plan_courses,
    replan_course,
)
from app.services.travel import Point, TravelService, get_travel_service

router = APIRouter(prefix="/courses", tags=["courses"])

_LOAD_STOPS = selectinload(Course.stops).selectinload(CourseStop.place)


def _plan_response(outcome: PlanOutcome) -> CoursePlanResponse:
    return CoursePlanResponse(
        group_id=outcome.group_id,
        courses=[CourseRead.model_validate(c) for c in outcome.courses],
        warnings=outcome.warnings,
    )


def _raise(exc: PlanError):
    raise HTTPException(status_code=exc.status_code, detail=exc.detail)


def _load_course(db: Session, course_id: str) -> Course | None:
    return db.scalar(select(Course).options(_LOAD_STOPS).where(Course.id == course_id))


def _get_viewable_course(db: Session, user: User, course_id: str) -> Course:
    course = _load_course(db, course_id)
    # 권한이 없어도 404 로 응답해서 코스 존재 여부를 알려주지 않습니다.
    if course is None or not can_view_course(db, user.id, course):
        raise HTTPException(status_code=404, detail="course not found")
    return course


def _get_owned_course(db: Session, user: User, course_id: str) -> Course:
    course = _load_course(db, course_id)
    if course is None or course.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="course not found")
    return course


def _summary(c: Course) -> CourseSummary:
    read = CourseRead.model_validate(c)
    return CourseSummary(
        id=c.id,
        group_id=c.group_id,
        title=c.title,
        course_date=c.course_date,
        created_at=c.created_at,
        priority_type=c.priority_type,  # type: ignore[arg-type]
        is_active=c.is_active,
        status=c.status,  # type: ignore[arg-type]
        total_time=read.total_time,
        total_cost=read.total_cost,
        stop_count=len(c.stops),
        place_names=[s.place.name for s in c.stops],
    )


@router.post("", response_model=CoursePlanResponse, status_code=status.HTTP_201_CREATED)
def create_courses(
    body: CourseCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    travel: TravelService = Depends(get_travel_service),
):
    """장소 목록으로 '최단 시간 / 최소 도보 / 최저 비용' 코스 3개를 한 번에 만들어 저장합니다.

    - 영업시간은 요청에 직접 넣은 값 > 내가 저장한 값 > (없으면) 24시간 영업 가정 순으로 씁니다.
    - 영업시간/이동시간 때문에 못 가는 장소는 코스에서 빠지고 `excluded` 에 사유가 담깁니다.
    - 모든 시각은 출발일 0시부터 지난 분(`*_min`)이며, 사람이 읽는 `*_time`(HH:MM)과 `*_day_offset`(자정 넘김)도 함께 제공합니다.
    """
    try:
        specs = build_specs_from_inputs(
            db, hours_user_id=current_user.id, course_date=body.course_date, inputs=body.stops
        )
        outcome = plan_courses(
            db,
            owner_id=current_user.id,
            title=body.title or f"{body.course_date.isoformat()} 코스",
            course_date=body.course_date,
            start=Point(body.start.lat, body.start.lng),
            start_min=body.start_time.hour * 60 + body.start_time.minute,
            specs=specs,
            travel=travel,
        )
    except PlanError as exc:
        _raise(exc)
    return _plan_response(outcome)


@router.get("", response_model=list[CourseSummary])
def list_my_courses(
    only_active: bool = Query(default=True, description="true 면 3개 버전 중 선택된 것만 (히스토리용)"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Course)
        .options(_LOAD_STOPS)
        .where(Course.owner_user_id == current_user.id)
        .order_by(Course.created_at.desc(), Course.id)
        .limit(limit)
        .offset(offset)
    )
    if only_active:
        stmt = stmt.where(Course.is_active.is_(True))
    return [_summary(c) for c in db.scalars(stmt).all()]


@router.get("/shared/{share_uuid}", response_model=CourseRead)
def read_shared_course(share_uuid: str, db: Session = Depends(get_db)):
    """공유 링크용 조회. 로그인 없이 볼 수 있고, 소유자 정보는 담기지 않습니다."""
    course = db.scalar(select(Course).options(_LOAD_STOPS).where(Course.share_uuid == share_uuid))
    if course is None:
        raise HTTPException(status_code=404, detail="course not found")
    return course


@router.get("/groups/{group_id}", response_model=CoursePlanResponse)
def read_course_group(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """같은 요청에서 만든 3개 버전을 모두 돌려줍니다."""
    courses = db.scalars(
        select(Course).options(_LOAD_STOPS).where(Course.group_id == group_id).order_by(Course.created_at, Course.id)
    ).all()
    if not courses or not can_view_course(db, current_user.id, courses[0]):
        raise HTTPException(status_code=404, detail="course group not found")
    order = {"time": 0, "walk": 1, "cost": 2}
    courses = sorted(courses, key=lambda c: order.get(c.priority_type, 9))
    return CoursePlanResponse(group_id=group_id, courses=[CourseRead.model_validate(c) for c in courses])


@router.get("/{course_id}", response_model=CourseRead)
def read_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_viewable_course(db, current_user, course_id)


@router.patch("/{course_id}", response_model=CourseRead)
def rename_course(
    course_id: str,
    body: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = _get_owned_course(db, current_user, course_id)
    course.title = body.title
    db.commit()
    db.refresh(course)
    return course


@router.post("/{course_id}/activate", response_model=CourseRead)
def activate_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """3개 버전 중 이 코스를 '선택된 버전'으로 바꿉니다. 그룹에 연결된 코스라면 그룹도 이 버전을 가리킵니다."""
    course = _get_owned_course(db, current_user, course_id)

    sibling_ids = list(db.scalars(select(Course.id).where(Course.group_id == course.group_id)))
    linked = db.scalar(select(GroupSession).where(GroupSession.course_id.in_(sibling_ids)))
    if linked is not None:
        # course_id 는 unique 이므로 비웠다가 새 값으로 채웁니다.
        linked.course_id = None
        db.flush()

    # 부분 유니크 인덱스(그룹당 활성 1개)에 걸리지 않게 먼저 모두 끄고 하나만 켭니다.
    db.execute(update(Course).where(Course.group_id == course.group_id).values(is_active=False))
    db.execute(update(Course).where(Course.id == course.id).values(is_active=True))
    if linked is not None:
        linked.course_id = course.id
    db.commit()
    db.expire_all()
    return _load_course(db, course_id)


@router.post("/{course_id}/replan", response_model=CoursePlanResponse, status_code=status.HTTP_201_CREATED)
def replan(
    course_id: str,
    body: ReplanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    travel: TravelService = Depends(get_travel_service),
):
    """현재 위치·시각 기준으로 남은 장소만 다시 계산합니다. (예: 30분 더 머무르기)

    - 내 코스이면 같은 코스(3개 버전)를 **덮어써서 갱신**합니다. 코스 ID, 공유 링크, 히스토리 항목은 그대로입니다.
    - 다른 사람의 코스(그룹 멤버로 열람)이면 원래 코스는 그대로 두고, 내 새 코스 3개를 만듭니다.
    - 체류시간은 `stay_adjustments` 로 장소별 증감(분)을 줍니다. 영업시간은 원래 코스에 저장된 값을 씁니다.
    """
    course = _get_viewable_course(db, current_user, course_id)
    in_place = course.owner_user_id == current_user.id
    try:
        outcome = replan_course(
            db, course=course, owner_id=current_user.id, req=body, travel=travel, in_place=in_place
        )
    except PlanError as exc:
        _raise(exc)
    return _plan_response(outcome)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """코스를 삭제합니다. 3개 버전이 한 묶음이라 같은 group_id 의 코스를 모두 지웁니다."""
    course = _get_owned_course(db, current_user, course_id)
    siblings = db.scalars(select(Course).where(Course.group_id == course.group_id)).all()
    sibling_ids = [c.id for c in siblings]
    if db.scalar(select(GroupSession.id).where(GroupSession.course_id.in_(sibling_ids))) is not None:
        raise HTTPException(status_code=409, detail="그룹에 연결된 코스는 삭제할 수 없습니다")
    for c in siblings:
        db.delete(c)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

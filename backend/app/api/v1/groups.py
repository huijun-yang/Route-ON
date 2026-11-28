import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.api.v1.courses import _plan_response
from app.core.database import get_db
from app.models import (
    Course,
    GroupCandidatePlace,
    GroupMember,
    GroupSession,
    Place,
    User,
    Vote,
)
from app.schemas.course import CoursePlanResponse, StopInput
from app.schemas.group import (
    CandidateCreate,
    CandidateRead,
    GroupCreate,
    GroupFinalizeRequest,
    GroupJoin,
    GroupMemberRead,
    GroupRead,
    GroupSummary,
)
from app.services.course_planner import PlanError, build_specs_from_inputs, plan_courses
from app.services.travel import Point, TravelService, get_travel_service

router = APIRouter(prefix="/groups", tags=["groups"])

# 헷갈리기 쉬운 문자(0/O, 1/I)를 뺀 초대코드 문자셋
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8


def _new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def _membership(db: Session, group_id: str, user_id: str) -> GroupMember | None:
    return db.get(GroupMember, (group_id, user_id))


def _get_group_as_member(db: Session, user: User, group_id: str) -> tuple[GroupSession, GroupMember]:
    group = db.get(GroupSession, group_id)
    member = _membership(db, group_id, user.id) if group else None
    # 멤버가 아니면 존재 여부를 숨기려고 404 로 응답합니다.
    if group is None or member is None:
        raise HTTPException(status_code=404, detail="group not found")
    return group, member


def _require_open(group: GroupSession) -> None:
    if group.status != "open":
        raise HTTPException(status_code=409, detail="이미 마감된 그룹입니다")


def _build_group_read(db: Session, group: GroupSession, me: GroupMember) -> GroupRead:
    members = db.execute(
        select(GroupMember, User.nickname)
        .join(User, User.id == GroupMember.user_id)
        .where(GroupMember.group_session_id == group.id)
        .order_by(GroupMember.joined_at, GroupMember.user_id)
    ).all()
    nick = {m.user_id: n for m, n in members}

    candidates = db.scalars(
        select(GroupCandidatePlace)
        .options(selectinload(GroupCandidatePlace.votes), selectinload(GroupCandidatePlace.place))
        .where(GroupCandidatePlace.group_session_id == group.id)
    ).all()
    cand_reads = [
        CandidateRead(
            id=c.id,
            place=c.place,
            added_by_user_id=c.added_by_user_id,
            added_by_nickname=nick.get(c.added_by_user_id),
            vote_count=len(c.votes),
            voted_by_me=any(v.user_id == me.user_id for v in c.votes),
        )
        for c in candidates
    ]
    cand_reads.sort(key=lambda c: (-c.vote_count, c.place.name))

    course_group_id = None
    if group.course_id:
        course_group_id = db.scalar(select(Course.group_id).where(Course.id == group.course_id))

    return GroupRead(
        id=group.id,
        title=group.title,
        invite_code=group.invite_code,
        status=group.status,
        course_id=group.course_id,
        course_group_id=course_group_id,
        my_role=me.role,
        members=[
            GroupMemberRead(user_id=m.user_id, nickname=n, role=m.role, joined_at=m.joined_at)
            for m, n in members
        ],
        candidates=cand_reads,
    )


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(
    body: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """그룹(모임)을 만들고 나를 대표(owner)로 등록합니다. 초대코드를 친구에게 공유하세요."""
    for _ in range(5):
        group = GroupSession(title=body.title, invite_code=_new_code(), status="open")
        group.members.append(GroupMember(user_id=current_user.id, role="owner"))
        db.add(group)
        try:
            db.commit()
            break
        except IntegrityError:  # 초대코드 충돌: 다시 뽑습니다.
            db.rollback()
    else:
        raise HTTPException(status_code=500, detail="could not generate invite code")
    db.refresh(group)
    return _build_group_read(db, group, _membership(db, group.id, current_user.id))


@router.post("/join", response_model=GroupRead)
def join_group(
    body: GroupJoin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """초대코드로 그룹에 참여합니다. 이미 참여 중이면 그대로 그룹 정보를 돌려줍니다."""
    group = db.scalar(select(GroupSession).where(GroupSession.invite_code == body.invite_code.strip().upper()))
    if group is None:
        raise HTTPException(status_code=404, detail="invalid invite code")
    member = _membership(db, group.id, current_user.id)
    if member is None:
        _require_open(group)
        member = GroupMember(group_session_id=group.id, user_id=current_user.id, role="member")
        db.add(member)
        try:
            db.commit()
        except IntegrityError:  # 동시에 두 번 참여 요청
            db.rollback()
            member = _membership(db, group.id, current_user.id)
    db.refresh(group)
    return _build_group_read(db, group, member)


@router.get("", response_model=list[GroupSummary])
def list_my_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.execute(
        select(GroupSession, GroupMember.role)
        .join(GroupMember, GroupMember.group_session_id == GroupSession.id)
        .where(GroupMember.user_id == current_user.id)
        .order_by(GroupSession.id)
    ).all()
    out = []
    for group, role in rows:
        member_count = db.scalar(select(func.count()).select_from(GroupMember).where(GroupMember.group_session_id == group.id))
        cand_count = db.scalar(
            select(func.count()).select_from(GroupCandidatePlace).where(GroupCandidatePlace.group_session_id == group.id)
        )
        out.append(
            GroupSummary(
                id=group.id,
                title=group.title,
                invite_code=group.invite_code,
                status=group.status,
                my_role=role,
                member_count=member_count or 0,
                candidate_count=cand_count or 0,
                course_id=group.course_id,
            )
        )
    return out


@router.get("/{group_id}", response_model=GroupRead)
def read_group(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    group, me = _get_group_as_member(db, current_user, group_id)
    return _build_group_read(db, group, me)


@router.post("/{group_id}/candidates", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def add_candidate(
    group_id: str,
    body: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """후보 장소를 추가합니다. 같은 장소가 이미 후보면 중복으로 만들지 않고 409 를 돌려줍니다."""
    group, me = _get_group_as_member(db, current_user, group_id)
    _require_open(group)
    if db.get(Place, body.place_id) is None:
        raise HTTPException(status_code=404, detail="place not found (save it first with POST /places)")
    exists = db.scalar(
        select(GroupCandidatePlace.id).where(
            GroupCandidatePlace.group_session_id == group_id, GroupCandidatePlace.place_id == body.place_id
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail="이미 후보에 있는 장소입니다")
    db.add(GroupCandidatePlace(group_session_id=group_id, place_id=body.place_id, added_by_user_id=current_user.id))
    db.commit()
    return _build_group_read(db, group, me)


def _get_candidate(db: Session, group_id: str, candidate_id: str) -> GroupCandidatePlace:
    cand = db.get(GroupCandidatePlace, candidate_id)
    if cand is None or cand.group_session_id != group_id:
        raise HTTPException(status_code=404, detail="candidate not found")
    return cand


@router.delete("/{group_id}/candidates/{candidate_id}", response_model=GroupRead)
def remove_candidate(
    group_id: str,
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """후보를 삭제합니다. 후보를 추가한 사람이나 그룹 대표만 삭제할 수 있고, 투표도 함께 지워집니다."""
    group, me = _get_group_as_member(db, current_user, group_id)
    _require_open(group)
    cand = _get_candidate(db, group_id, candidate_id)
    if me.role != "owner" and cand.added_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="후보를 추가한 사람이나 대표만 삭제할 수 있습니다")
    db.delete(cand)
    db.commit()
    return _build_group_read(db, group, me)


@router.post("/{group_id}/candidates/{candidate_id}/vote", response_model=GroupRead)
def vote(
    group_id: str,
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """투표합니다. 이미 투표했다면 아무 일도 일어나지 않습니다(중복 안 됨)."""
    group, me = _get_group_as_member(db, current_user, group_id)
    _require_open(group)
    _get_candidate(db, group_id, candidate_id)
    already = db.scalar(
        select(Vote.id).where(Vote.candidate_place_id == candidate_id, Vote.user_id == current_user.id)
    )
    if not already:
        db.add(Vote(candidate_place_id=candidate_id, user_id=current_user.id))
        try:
            db.commit()
        except IntegrityError:  # 동시에 두 번 눌렀을 때 unique 제약이 막아줍니다.
            db.rollback()
    return _build_group_read(db, group, me)


@router.delete("/{group_id}/candidates/{candidate_id}/vote", response_model=GroupRead)
def unvote(
    group_id: str,
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group, me = _get_group_as_member(db, current_user, group_id)
    _require_open(group)
    _get_candidate(db, group_id, candidate_id)
    row = db.scalar(select(Vote).where(Vote.candidate_place_id == candidate_id, Vote.user_id == current_user.id))
    if row is not None:
        db.delete(row)
        db.commit()
    return _build_group_read(db, group, me)


@router.post("/{group_id}/finalize", response_model=CoursePlanResponse, status_code=status.HTTP_201_CREATED)
def finalize_group(
    group_id: str,
    body: GroupFinalizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    travel: TravelService = Depends(get_travel_service),
):
    """투표를 마감하고, 득표 상위 장소로 코스 3개를 만들어 그룹에 연결합니다. (대표만 가능)

    - 1표 이상 받은 후보가 있으면 그 후보들만, 아무도 투표하지 않았으면 오류(422)입니다.
    - 영업시간은 그룹 대표가 저장한 값을 씁니다. 코스는 모든 멤버가 볼 수 있습니다.
    """
    group, me = _get_group_as_member(db, current_user, group_id)
    if me.role != "owner":
        raise HTTPException(status_code=403, detail="그룹 대표만 코스를 확정할 수 있습니다")
    _require_open(group)

    candidates = db.scalars(
        select(GroupCandidatePlace)
        .options(selectinload(GroupCandidatePlace.votes))
        .where(GroupCandidatePlace.group_session_id == group_id)
    ).all()
    voted = [c for c in candidates if len(c.votes) > 0]
    if not voted:
        raise HTTPException(status_code=422, detail="투표를 받은 후보 장소가 없습니다")
    voted.sort(key=lambda c: (-len(c.votes), c.id))
    chosen = voted[: body.max_places]

    inputs = [
        StopInput(place_id=c.place_id, stay_min=body.stay_overrides.get(c.place_id, body.default_stay_min))
        for c in chosen
    ]
    try:
        specs = build_specs_from_inputs(db, hours_user_id=current_user.id, course_date=body.course_date, inputs=inputs)
        outcome = plan_courses(
            db,
            owner_id=current_user.id,
            title=body.title or group.title or f"{body.course_date.isoformat()} 그룹 코스",
            course_date=body.course_date,
            start=Point(body.start.lat, body.start.lng),
            start_min=body.start_time.hour * 60 + body.start_time.minute,
            specs=specs,
            travel=travel,
        )
    except PlanError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    active = next((c for c in outcome.courses if c.is_active), outcome.courses[0])
    group.course_id = active.id
    group.status = "closed"
    db.commit()
    return _plan_response(outcome)


@router.delete("/{group_id}/members/me", status_code=status.HTTP_204_NO_CONTENT)
def leave_group(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """그룹에서 나갑니다. 대표는 나갈 수 없고, 그룹 삭제를 사용해야 합니다."""
    group, me = _get_group_as_member(db, current_user, group_id)
    if me.role == "owner":
        raise HTTPException(status_code=409, detail="대표는 나갈 수 없습니다. 그룹을 삭제하세요")
    db.delete(me)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """그룹을 삭제합니다 (대표만). 후보·투표·멤버가 함께 지워지고, 이미 만든 코스는 남습니다."""
    group, me = _get_group_as_member(db, current_user, group_id)
    if me.role != "owner":
        raise HTTPException(status_code=403, detail="그룹 대표만 삭제할 수 있습니다")
    db.delete(group)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

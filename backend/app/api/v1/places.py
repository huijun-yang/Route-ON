from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import BusinessHours, Place, User
from app.schemas.business_hours import BusinessHoursCreate, BusinessHoursRead
from app.schemas.place import PlaceCreate, PlaceRead

router = APIRouter(prefix="/places", tags=["places"])

# 주의: 나중에 GET /places/search 를 추가할 때는 GET /{place_id} 보다 위에 선언해야 합니다.

PlaceId = Path(min_length=1, max_length=50)


def _get_place_or_404(db: Session, place_id: str) -> Place:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="place not found (save it first with POST /places)")
    return place


@router.post("", response_model=PlaceRead, status_code=status.HTTP_201_CREATED)
def save_place(
    body: PlaceCreate,
    response: Response,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """장소를 저장합니다. 이미 있는 장소면 덮어쓰지 않고 기존 값을 그대로 돌려줍니다(200)."""
    place = db.get(Place, body.kakao_place_id)
    if place is not None:
        response.status_code = status.HTTP_200_OK
        return place

    place = Place(**body.model_dump())
    db.add(place)
    try:
        db.commit()
    except IntegrityError:
        # 동시에 같은 장소를 저장한 경우: 먼저 저장된 값을 사용합니다.
        db.rollback()
        place = db.get(Place, body.kakao_place_id)
        if place is None:
            raise
        response.status_code = status.HTTP_200_OK
        return place
    db.refresh(place)
    return place


@router.get("/{place_id}", response_model=PlaceRead)
def read_place(place_id: str = PlaceId, db: Session = Depends(get_db)):
    return _get_place_or_404(db, place_id)


@router.post(
    "/{place_id}/business-hours",
    response_model=BusinessHoursRead,
    status_code=status.HTTP_201_CREATED,
)
def upsert_business_hours(
    body: BusinessHoursCreate,
    response: Response,
    place_id: str = PlaceId,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """내 영업시간을 저장합니다. 같은 (장소, 요일)이 이미 있으면 수정합니다(200).

    영업시간은 사용자 개인 계정에만 저장되고 다른 사용자에게 공유되지 않습니다.
    """
    _get_place_or_404(db, place_id)

    def apply(row: BusinessHours) -> None:
        row.open_time = body.open_time
        row.close_time = body.close_time
        row.break_start = body.break_start
        row.break_end = body.break_end

    key = (current_user.id, place_id, body.weekday)
    row = db.get(BusinessHours, key)
    if row is not None:
        apply(row)
        response.status_code = status.HTTP_200_OK
    else:
        row = BusinessHours(user_id=current_user.id, place_id=place_id, weekday=body.weekday)
        apply(row)
        db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # 같은 요일을 동시에 처음 저장한 경우: 먼저 저장된 행을 수정합니다.
        db.rollback()
        row = db.get(BusinessHours, key)
        if row is None:
            raise
        apply(row)
        db.commit()
        response.status_code = status.HTTP_200_OK
    db.refresh(row)
    return row


@router.get("/{place_id}/business-hours", response_model=list[BusinessHoursRead])
def list_my_business_hours(
    place_id: str = PlaceId,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """이 장소에 대해 내가 저장한 요일별 영업시간을 요일 순으로 돌려줍니다."""
    _get_place_or_404(db, place_id)
    rows = db.scalars(
        select(BusinessHours)
        .where(BusinessHours.user_id == current_user.id, BusinessHours.place_id == place_id)
        .order_by(BusinessHours.weekday)
    ).all()
    return rows


@router.delete("/{place_id}/business-hours/{weekday}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_business_hours(
    weekday: int = Path(ge=0, le=6),
    place_id: str = PlaceId,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.get(BusinessHours, (current_user.id, place_id, weekday))
    if row is None:
        raise HTTPException(status_code=404, detail="business hours not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

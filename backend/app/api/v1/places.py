from dataclasses import dataclass
from datetime import date as date_type

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import BusinessHours, BusinessHoursException, Place, User
from app.schemas.business_hours import (
    BusinessHoursCreate,
    BusinessHoursExceptionCreate,
    BusinessHoursExceptionRead,
    BusinessHoursRead,
)
from app.schemas.place import PlaceCreate, PlaceRead
from app.services.stay_time import recommend_stay
from app.services.kakao import (
    KakaoNotConfiguredError,
    KakaoServiceError,
    get_kakao_client,
    search_places,
)

router = APIRouter(prefix="/places", tags=["places"])

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


@dataclass(frozen=True)
class _SearchAttempt:
    query: str
    lat: float | None
    lng: float | None
    radius: int | None


def _search_attempts(
    query: str, lat: float | None, lng: float | None, radius: int | None, page: int
) -> list[_SearchAttempt]:
    """검색어로 결과가 없을 때 차례로 시도할 조건들.

    카카오 키워드 검색은 검색어가 길거나(예: "경희대학교 서울캠퍼스") 반경 안에 장소가 없으면 빈 결과를 줍니다.
    그래서 ① 요청 그대로 → ② 반경 없이 → ③ 마지막 단어를 하나씩 줄여가며(최대 2번) 찾습니다.
    첫 페이지 검색에서만 이렇게 넓히고, 다음 페이지는 요청 그대로만 조회합니다.
    """
    attempts = [_SearchAttempt(query, lat, lng, radius)]
    if page > 1:
        return attempts
    if lat is not None:
        attempts.append(_SearchAttempt(query, None, None, None))
    words = query.split()
    for _ in range(2):
        if len(words) <= 1:
            break
        words = words[:-1]
        attempts.append(_SearchAttempt(" ".join(words), None, None, None))
    return attempts


# 주의: GET /search 는 GET /{place_id} 보다 위에 선언해야 합니다. (아니면 "search" 가 장소 ID 로 해석됨)
@router.get("/search", response_model=list[PlaceCreate])
def search_kakao_places(
    query: str = Query(min_length=1, max_length=100, description="검색어 (예: 성수 카페)"),
    lat: float | None = Query(default=None, ge=-90, le=90, description="이 위치 주변을 우선 검색"),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius: int | None = Query(default=None, ge=1, le=20000, description="반경(m), lat/lng 와 함께 사용"),
    size: int = Query(default=10, ge=1, le=15),
    page: int = Query(default=1, ge=1, le=45),
    client: httpx.Client = Depends(get_kakao_client),
    _user: User = Depends(get_current_user),
):
    """카카오 로컬 API 로 장소를 검색합니다. 결과는 그대로 POST /places 에 보낼 수 있는 형태입니다."""
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=422, detail="lat 와 lng 는 함께 보내야 합니다")
    try:
        found = []
        for attempt in _search_attempts(query, lat, lng, radius, page):
            found = search_places(
                attempt.query,
                client,
                settings.kakao_rest_api_key,
                lat=attempt.lat,
                lng=attempt.lng,
                radius_m=attempt.radius,
                size=size,
                page=page,
            )
            if found:
                break
    except KakaoNotConfiguredError:
        raise HTTPException(status_code=503, detail="장소 검색이 설정되지 않았습니다 (KAKAO_REST_API_KEY)")
    except KakaoServiceError:
        raise HTTPException(status_code=502, detail="kakao service unavailable")
    return [
        PlaceCreate(
            kakao_place_id=p.kakao_place_id, name=p.name, address=p.address, lat=p.lat, lng=p.lng, category=p.category
        )
        for p in found
    ]


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
        row.is_closed = body.is_closed
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


@router.get("/{place_id}/recommended-stay")
def get_recommended_stay(place_id: str = PlaceId, db: Session = Depends(get_db)):
    """장소 유형(카테고리)에 따른 추천 체류시간(분). 코스 생성 때 stay_min 을 비우면 이 값이 쓰입니다."""
    place = _get_place_or_404(db, place_id)
    return {"place_id": place_id, "category": place.category, "recommended_stay_min": recommend_stay(place.category)}


@router.post(
    "/{place_id}/business-hours/exceptions",
    response_model=BusinessHoursExceptionRead,
    status_code=status.HTTP_201_CREATED,
)
def upsert_business_hours_exception(
    body: BusinessHoursExceptionCreate,
    response: Response,
    place_id: str = PlaceId,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """특정 날짜 하나에만 적용되는 영업시간(임시휴무: is_closed=true)을 저장합니다. 같은 날짜가 있으면 수정합니다(200).

    요일별 영업시간보다 우선하고, 코스 요청에 직접 넣은 `hours` 보다는 후순위입니다.
    """
    _get_place_or_404(db, place_id)

    def apply(row: BusinessHoursException) -> None:
        row.is_closed = body.is_closed
        row.open_time = body.open_time
        row.close_time = body.close_time
        row.break_start = body.break_start
        row.break_end = body.break_end

    key = (current_user.id, place_id, body.date)
    row = db.get(BusinessHoursException, key)
    if row is not None:
        apply(row)
        response.status_code = status.HTTP_200_OK
    else:
        row = BusinessHoursException(user_id=current_user.id, place_id=place_id, date=body.date)
        apply(row)
        db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        row = db.get(BusinessHoursException, key)
        if row is None:
            raise
        apply(row)
        db.commit()
        response.status_code = status.HTTP_200_OK
    db.refresh(row)
    return row


@router.get("/{place_id}/business-hours/exceptions", response_model=list[BusinessHoursExceptionRead])
def list_my_business_hours_exceptions(
    place_id: str = PlaceId,
    from_date: date_type | None = Query(default=None, description="이 날짜 이후(포함)만"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """이 장소에 대해 내가 저장한 날짜별 예외를 날짜 순으로 돌려줍니다."""
    _get_place_or_404(db, place_id)
    stmt = select(BusinessHoursException).where(
        BusinessHoursException.user_id == current_user.id, BusinessHoursException.place_id == place_id
    )
    if from_date is not None:
        stmt = stmt.where(BusinessHoursException.date >= from_date)
    return db.scalars(stmt.order_by(BusinessHoursException.date)).all()


@router.delete("/{place_id}/business-hours/exceptions/{day}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_business_hours_exception(
    day: date_type,
    place_id: str = PlaceId,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.get(BusinessHoursException, (current_user.id, place_id, day))
    if row is None:
        raise HTTPException(status_code=404, detail="business hours exception not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

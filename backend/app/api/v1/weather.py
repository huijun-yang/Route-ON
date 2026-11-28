from datetime import date, datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import settings
from app.models import User
from app.services.weather import (
    WeatherError,
    WeatherNotConfiguredError,
    fetch_weather,
    latlng_to_grid,
)

router = APIRouter(prefix="/weather", tags=["weather"])

KST = timezone(timedelta(hours=9))


class WeatherRead(BaseModel):
    available: bool
    reason: str | None = None  # forecast_out_of_range 등
    date: date
    hour: int
    temp_c: float | None = None
    sky: str | None = None
    precipitation: str | None = None
    pop: int | None = None
    summary: str | None = None
    grid: tuple[int, int]


def get_weather_client():
    with httpx.Client(timeout=5.0) as client:
        yield client


@router.get("", response_model=WeatherRead)
def read_weather(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    on: date | None = Query(default=None, alias="date", description="방문일 (기본: 오늘)"),
    hour: int = Query(default=12, ge=0, le=23, description="알고 싶은 시각(시)"),
    client: httpx.Client = Depends(get_weather_client),
    _user: User = Depends(get_current_user),
):
    """방문일의 날씨를 기상청 단기예보로 조회합니다. 예보 범위(약 3일)를 벗어나면 available=false 입니다."""
    now = datetime.now(KST)
    target = on or now.date()
    grid = latlng_to_grid(lat, lng)
    try:
        info = fetch_weather(client, settings.kma_api_key, lat, lng, target, hour, now)
    except WeatherNotConfiguredError:
        raise HTTPException(status_code=503, detail="날씨 조회가 설정되지 않았습니다 (KMA_API_KEY)")
    except WeatherError:
        raise HTTPException(status_code=502, detail="weather service unavailable")
    return WeatherRead(
        available=info.available,
        reason=info.reason,
        date=target,
        hour=hour,
        temp_c=info.temp_c,
        sky=info.sky,
        precipitation=info.precipitation,
        pop=info.pop,
        summary=info.summary,
        grid=grid,
    )

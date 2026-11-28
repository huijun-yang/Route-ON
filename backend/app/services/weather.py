"""기상청 단기예보(공공데이터포털) 조회.

- 위경도를 기상청 격자(nx, ny)로 바꾼 뒤 getVilageFcst 를 호출합니다.
- 단기예보는 발표 시각(02,05,08,11,14,17,20,23시, 발표 약 10분 후 제공) 기준으로 오늘부터 약 3일치를 줍니다.
  그래서 방문일이 그보다 멀면 'available=False' 로 돌려줍니다. (오류가 아님)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import httpx

KMA_VILAGE_FCST_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
BASE_HOURS = (2, 5, 8, 11, 14, 17, 20, 23)

SKY = {"1": "맑음", "3": "구름많음", "4": "흐림"}
PTY = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}


class WeatherError(Exception):
    pass


class WeatherNotConfiguredError(Exception):
    pass


@dataclass
class WeatherInfo:
    available: bool
    reason: str | None = None
    temp_c: float | None = None
    sky: str | None = None
    precipitation: str | None = None  # 없음/비/눈...
    pop: int | None = None  # 강수확률(%)
    summary: str | None = None
    extra: dict = field(default_factory=dict)


def latlng_to_grid(lat: float, lng: float) -> tuple[int, int]:
    """위경도 → 기상청 격자 좌표(nx, ny). (기상청 제공 Lambert Conformal Conic 변환식)"""
    re = 6371.00877 / 5.0  # 지구 반경 / 격자 간격(km)
    slat1, slat2 = math.radians(30.0), math.radians(60.0)
    olon, olat = math.radians(126.0), math.radians(38.0)
    xo, yo = 43, 136

    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(
        math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    )
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5) ** sn * math.cos(slat1) / sn
    ro = re * sf / math.tan(math.pi * 0.25 + olat * 0.5) ** sn

    ra = re * sf / math.tan(math.pi * 0.25 + math.radians(lat) * 0.5) ** sn
    theta = math.radians(lng) - olon
    if theta > math.pi:
        theta -= 2 * math.pi
    if theta < -math.pi:
        theta += 2 * math.pi
    theta *= sn
    return int(ra * math.sin(theta) + xo + 0.5), int(ro - ra * math.cos(theta) + yo + 0.5)


def latest_base_time(now: datetime) -> tuple[str, str]:
    """지금 조회할 수 있는 가장 최근 발표 (base_date, base_time). 발표 후 10분 뒤부터 제공됩니다."""
    t = now - timedelta(minutes=10)
    candidates = [h for h in BASE_HOURS if h <= t.hour]
    if candidates:
        return t.strftime("%Y%m%d"), f"{candidates[-1]:02d}00"
    y = t - timedelta(days=1)  # 02시 발표 전이면 전날 23시 발표
    return y.strftime("%Y%m%d"), "2300"


def parse_forecast(items: list[dict], target_date: date, target_hour: int) -> WeatherInfo:
    """예보 항목들에서 target_date 의 target_hour 와 가장 가까운 시각의 값을 골라냅니다."""
    want = target_date.strftime("%Y%m%d")
    day_items = [i for i in items if i.get("fcstDate") == want]
    if not day_items:
        return WeatherInfo(False, reason="forecast_out_of_range")

    hours = sorted({int(i["fcstTime"][:2]) for i in day_items})
    pick = min(hours, key=lambda h: abs(h - target_hour))
    at = {i["category"]: i["fcstValue"] for i in day_items if int(i["fcstTime"][:2]) == pick}

    temp = float(at["TMP"]) if "TMP" in at else None
    sky = SKY.get(at.get("SKY", ""))
    pty = PTY.get(at.get("PTY", "0"), "없음")
    pop = int(at["POP"]) if "POP" in at else None

    parts = []
    if pty != "없음":
        parts.append(pty)
    elif sky:
        parts.append(sky)
    if temp is not None:
        parts.append(f"{temp:g}°C")
    if pop is not None:
        parts.append(f"강수확률 {pop}%")
    return WeatherInfo(
        True,
        temp_c=temp,
        sky=sky,
        precipitation=pty,
        pop=pop,
        summary=" · ".join(parts) or None,
        extra={"forecast_hour": pick},
    )


def fetch_weather(
    client: httpx.Client, api_key: str, lat: float, lng: float, target_date: date, target_hour: int, now: datetime
) -> WeatherInfo:
    if not api_key:
        raise WeatherNotConfiguredError("KMA_API_KEY is not set")
    nx, ny = latlng_to_grid(lat, lng)
    base_date, base_time = latest_base_time(now)
    try:
        resp = client.get(
            KMA_VILAGE_FCST_URL,
            params={
                "serviceKey": api_key,
                "pageNo": 1,
                "numOfRows": 1000,
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": nx,
                "ny": ny,
            },
        )
    except httpx.HTTPError as exc:
        raise WeatherError(f"request failed: {exc.__class__.__name__}") from exc
    if resp.status_code != 200:
        raise WeatherError(f"kma returned status {resp.status_code}")
    try:
        body = resp.json()["response"]
        header = body["header"]
        if header.get("resultCode") != "00":
            raise WeatherError(f"kma error: {header.get('resultMsg')}")
        items = body["body"]["items"]["item"]
    except (ValueError, KeyError, TypeError) as exc:
        # 키가 잘못되면 JSON 이 아니라 XML 오류가 올 수 있어 ValueError 도 여기서 처리합니다.
        raise WeatherError("unexpected response from kma") from exc
    return parse_forecast(items, target_date, target_hour)

"""장소 사이 이동시간 계산.

흐름
  1) DB 캐시(travel_time_cache)에 있으면 그 값을 씁니다.
  2) 없으면 Tmap 으로 조회하고(키가 있을 때), 결과를 캐시에 저장합니다.
       - 걸어갈 만한 거리(WALK_ONLY_MAX_M 이하)는 Tmap 보행자 경로 API (도보 시간·거리가 정확함)
       - 그보다 먼 구간은 Tmap 대중교통 API
     두 API 는 상품·호출 한도가 따로라서, 한쪽이 막혀도 다른 쪽은 계속 씁니다.
  3) 키가 없거나 호출이 실패하면 직선거리 기반 '추정값'으로 대신합니다. (추정값은 캐시하지 않음)

호출 횟수를 줄이려고 A→B 와 B→A 는 같은 값으로 보고 한 방향만 조회합니다. (장소 n개 → 구간 n(n+1)/2 개)
실패한 이유는 TravelService.issues 에 모아 두었다가 코스 응답의 warnings 에 보여줍니다.

그래서 Tmap 키 없이도 코스 생성이 동작하고, API 장애가 나도 서비스가 멈추지 않습니다.
"""
from __future__ import annotations

import math
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import TravelTimeCache

TMAP_TRANSIT_URL = "https://apis.openapi.sk.com/transit/routes"
TMAP_PEDESTRIAN_URL = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1"
CACHE_TTL = timedelta(days=7)
MAX_PARALLEL_CALLS = 5

# --- 추정값 파라미터 (Tmap 을 쓸 수 없을 때) ---
DETOUR_FACTOR = 1.3  # 직선거리 → 실제 도로 거리 보정
WALK_M_PER_MIN = 80  # 도보 약 4.8km/h
WALK_ONLY_MAX_M = 1500  # 이 이하면 걸어서 이동한다고 봄
TRANSIT_M_PER_MIN = 330  # 대중교통 약 20km/h (정차·환승 포함)
TRANSIT_OVERHEAD_MIN = 10  # 대기 + 승하차
TRANSIT_ACCESS_WALK_M = 600  # 정류장까지 걷는 거리(왕복 합)
TRANSIT_BASE_FARE = 1500  # 기본요금(원), 추정용


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float


@dataclass(frozen=True)
class Leg:
    """한 구간(A→B) 이동 정보."""

    travel_min: int
    walk_min: int = 0
    walk_m: int = 0
    fare: int = 0
    source: str = "estimate"  # "tmap" | "cache" | "estimate" | "same"


ZERO_LEG = Leg(0, 0, 0, 0, "same")


class TmapError(Exception):
    def __init__(self, message: str, *, fatal: bool = False):
        super().__init__(message)
        self.fatal = fatal  # True 면 키/쿼터 문제라 같은 요청에서 더 시도하지 않음


def _http_issue(status: int) -> str:
    """Tmap 이 돌려준 HTTP 상태를 사람이 읽을 수 있는 원인으로 바꿉니다."""
    if status == 429:
        return "호출 한도 초과(429)"
    if status in (401, 403):
        return f"API 키 오류 또는 해당 상품 미신청({status})"
    return f"응답 오류({status})"


def haversine_m(a: Point, b: Point) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dphi = p2 - p1
    dlmb = math.radians(b.lng - a.lng)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def estimate_leg(a: Point, b: Point) -> Leg:
    """직선거리로 이동시간·도보량·요금을 어림잡습니다."""
    straight = haversine_m(a, b)
    if straight < 1:
        return Leg(0, 0, 0, 0, "same")
    road = straight * DETOUR_FACTOR
    if road <= WALK_ONLY_MAX_M:
        minutes = max(1, math.ceil(road / WALK_M_PER_MIN))
        return Leg(minutes, minutes, round(road), 0, "estimate")
    walk_m = TRANSIT_ACCESS_WALK_M
    walk_min = math.ceil(walk_m / WALK_M_PER_MIN)
    minutes = TRANSIT_OVERHEAD_MIN + math.ceil(road / TRANSIT_M_PER_MIN)
    return Leg(minutes, walk_min, walk_m, TRANSIT_BASE_FARE, "estimate")


def parse_tmap_transit(data: dict) -> Leg:
    """Tmap 대중교통 경로 응답에서 가장 빠른 경로를 골라 Leg 로 바꿉니다.

    응답 구조(문서 기준): metaData.plan.itineraries[] 각 항목에
      totalTime(초), walkTime(초), walkDistance(m), fare.regular.totalFare(원)
    """
    itineraries = ((data.get("metaData") or {}).get("plan") or {}).get("itineraries") or []
    if not itineraries:
        # 오류 응답은 {"result": {"status": ..., "message": ...}} 형태로 오는 경우가 많습니다.
        result = data.get("result") or {}
        raise TmapError(f"no itinerary: {result.get('message') or 'empty response'}")
    best = min(itineraries, key=lambda it: it.get("totalTime", 10**9))
    total = best.get("totalTime")
    if total is None:
        raise TmapError("itinerary has no totalTime")
    fare = ((best.get("fare") or {}).get("regular") or {}).get("totalFare") or 0
    return Leg(
        travel_min=max(0, math.ceil(total / 60)),
        walk_min=max(0, math.ceil((best.get("walkTime") or 0) / 60)),
        walk_m=int(best.get("walkDistance") or 0),
        fare=int(fare),
        source="tmap",
    )


class TmapTransitClient:
    def __init__(self, client: httpx.Client, app_key: str):
        self._client = client
        self._app_key = app_key

    def get_leg(self, a: Point, b: Point, depart: datetime) -> Leg:
        body = {
            "startX": str(a.lng),
            "startY": str(a.lat),
            "endX": str(b.lng),
            "endY": str(b.lat),
            "count": 3,
            "lang": 0,
            "format": "json",
            "searchDttm": depart.strftime("%Y%m%d%H%M"),
        }
        try:
            resp = self._client.post(
                TMAP_TRANSIT_URL,
                headers={"appKey": self._app_key, "accept": "application/json", "content-type": "application/json"},
                json=body,
            )
        except httpx.HTTPError as exc:
            raise TmapError(f"request failed: {exc.__class__.__name__}") from exc
        if resp.status_code in (401, 403, 429):
            raise TmapError(_http_issue(resp.status_code), fatal=True)
        if resp.status_code != 200:
            raise TmapError(_http_issue(resp.status_code))
        try:
            return parse_tmap_transit(resp.json())
        except ValueError as exc:
            raise TmapError("invalid json") from exc


def parse_tmap_pedestrian(data: dict) -> Leg:
    """Tmap 보행자 경로 응답(GeoJSON)에서 총 거리·시간을 꺼냅니다.

    features[0].properties 에 totalDistance(m), totalTime(초) 가 들어 있습니다.
    """
    features = data.get("features") or []
    if not features:
        raise TmapError("no pedestrian route")
    props = features[0].get("properties") or {}
    total_time, total_dist = props.get("totalTime"), props.get("totalDistance")
    if total_time is None or total_dist is None:
        raise TmapError("pedestrian route has no total")
    minutes = max(1, math.ceil(total_time / 60))
    return Leg(travel_min=minutes, walk_min=minutes, walk_m=int(total_dist), fare=0, source="tmap")


class TmapPedestrianClient:
    """Tmap 보행자 경로 API. 짧은 구간의 도보 시간을 정확하게 받아옵니다."""

    def __init__(self, client: httpx.Client, app_key: str):
        self._client = client
        self._app_key = app_key

    def get_leg(self, a: Point, b: Point, depart: datetime) -> Leg:  # depart 는 쓰지 않지만 인터페이스를 맞춥니다
        body = {
            "startX": a.lng,
            "startY": a.lat,
            "endX": b.lng,
            "endY": b.lat,
            "reqCoordType": "WGS84GEO",
            "resCoordType": "WGS84GEO",
            "startName": "start",
            "endName": "end",
        }
        try:
            resp = self._client.post(
                TMAP_PEDESTRIAN_URL,
                headers={"appKey": self._app_key, "accept": "application/json", "content-type": "application/json"},
                json=body,
            )
        except httpx.HTTPError as exc:
            raise TmapError(f"request failed: {exc.__class__.__name__}") from exc
        if resp.status_code in (401, 403, 429):
            raise TmapError(_http_issue(resp.status_code), fatal=True)
        if resp.status_code != 200:
            raise TmapError(_http_issue(resp.status_code))
        try:
            return parse_tmap_pedestrian(resp.json())
        except ValueError as exc:
            raise TmapError("invalid json") from exc


def _round(p: Point) -> str:
    return f"{p.lat:.4f},{p.lng:.4f}"


def cache_key(a: Point, b: Point, depart: datetime) -> str:
    # 요일 구분(평일/주말) + 시각(시) 단위로 묶습니다. 같은 좌표(약 11m)면 같은 구간으로 봅니다.
    bucket = f"{'we' if depart.weekday() >= 5 else 'wd'}{depart.hour:02d}"
    return f"{_round(a)}>{_round(b)}|{bucket}"


def _is_walkable(a: Point, b: Point) -> bool:
    """걸어갈 만한 거리인지. 추정값 계산과 같은 기준(직선거리 x 보정 계수 <= WALK_ONLY_MAX_M)을 씁니다."""
    return haversine_m(a, b) * DETOUR_FACTOR <= WALK_ONLY_MAX_M


class TravelService:
    """이동시간 행렬을 만들어 주는 서비스. 테스트에서는 tmap=None 으로 만들면 추정값만 씁니다."""

    def __init__(
        self,
        db: Session,
        tmap: TmapTransitClient | None,
        walker: TmapPedestrianClient | None = None,
    ):
        self.db = db
        self.tmap = tmap  # 대중교통
        self.walker = walker  # 보행자
        # 이번 요청에서 Tmap 호출이 실패한 이유들 (중복 없이, 순서 유지). 코스 응답의 경고에 사용합니다.
        self.issues: list[str] = []

    def _note(self, label: str, exc: TmapError) -> None:
        message = f"{label}: {exc}"
        if message not in self.issues:
            self.issues.append(message)

    def leg_matrix(self, points: list[Point], depart: datetime) -> list[list[Leg]]:
        """points[0] 이 출발지. 결과 [i][j] 는 i→j 이동 정보. (j→i 는 같은 값을 씁니다)"""
        n = len(points)
        matrix: list[list[Leg]] = [[ZERO_LEG] * n for _ in range(n)]
        pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]  # 한 방향만

        # 1) 캐시 조회 (한 번의 쿼리). 반대 방향으로 저장된 값도 같은 구간으로 봅니다.
        fwd_keys = {(i, j): cache_key(points[i], points[j], depart) for i, j in pairs}
        rev_keys = {(i, j): cache_key(points[j], points[i], depart) for i, j in pairs}
        cached: dict[str, TravelTimeCache] = {}
        if pairs:
            wanted = set(fwd_keys.values()) | set(rev_keys.values())
            rows = self.db.scalars(select(TravelTimeCache).where(TravelTimeCache.key.in_(wanted))).all()
            now = datetime.now(timezone.utc)
            for r in rows:
                created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
                if now - created <= CACHE_TTL:
                    cached[r.key] = r

        def put(i: int, j: int, leg: Leg) -> None:
            matrix[i][j] = leg
            matrix[j][i] = leg

        misses: list[tuple[int, int]] = []
        for i, j in pairs:
            row = cached.get(fwd_keys[(i, j)]) or cached.get(rev_keys[(i, j)])
            if row is not None:
                put(i, j, Leg(row.travel_min, row.walk_min, row.walk_m, row.fare, "cache"))
            elif haversine_m(points[i], points[j]) < 1:
                put(i, j, ZERO_LEG)
            else:
                misses.append((i, j))

        # 2) 캐시에 없는 구간: 가까우면 보행자 API, 멀면 대중교통 API. 실패하면 추정값.
        walk_pairs = [p for p in misses if _is_walkable(points[p[0]], points[p[1]])]
        walk_set = set(walk_pairs)
        transit_pairs = [p for p in misses if p not in walk_set]
        fetched: dict[tuple[int, int], Leg] = {}
        fetched.update(self._fetch(self.walker, "Tmap 보행자 경로", points, walk_pairs, depart))
        fetched.update(self._fetch(self.tmap, "Tmap 대중교통", points, transit_pairs, depart))

        new_rows: dict[str, TravelTimeCache] = {}
        for i, j in misses:
            leg = fetched.get((i, j))
            if leg is None:
                put(i, j, estimate_leg(points[i], points[j]))
                continue
            put(i, j, leg)
            key = fwd_keys[(i, j)]
            new_rows[key] = TravelTimeCache(
                key=key, travel_min=leg.travel_min, walk_min=leg.walk_min, walk_m=leg.walk_m, fare=leg.fare
            )
        if new_rows:
            self._save_cache(new_rows)
        return matrix

    def _fetch(
        self,
        client: TmapTransitClient | TmapPedestrianClient | None,
        label: str,
        points: list[Point],
        pairs: list[tuple[int, int]],
        depart: datetime,
    ) -> dict[tuple[int, int], Leg]:
        if not pairs or client is None:
            return {}
        result: dict[tuple[int, int], Leg] = {}

        # 첫 호출은 혼자 실행해서 키/쿼터 문제를 먼저 확인합니다. 치명적이면 나머지는 시도하지 않습니다.
        first = pairs[0]
        try:
            result[first] = client.get_leg(points[first[0]], points[first[1]], depart)
        except TmapError as exc:
            self._note(label, exc)
            if exc.fatal:
                return {}

        rest = pairs[1:]
        if rest:
            def call(pair: tuple[int, int]) -> tuple[tuple[int, int], Leg | None, TmapError | None]:
                try:
                    return pair, client.get_leg(points[pair[0]], points[pair[1]], depart), None
                except TmapError as exc:
                    return pair, None, exc

            with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CALLS) as pool:
                for pair, leg, error in pool.map(call, rest):
                    if leg is not None:
                        result[pair] = leg
                    elif error is not None:
                        self._note(label, error)
        return result

    def _save_cache(self, rows: dict[str, TravelTimeCache]) -> None:
        # 오래된 같은 키가 있으면 지우고 새로 저장합니다.
        self.db.query(TravelTimeCache).filter(TravelTimeCache.key.in_(list(rows))).delete(synchronize_session=False)
        self.db.add_all(rows.values())
        # 이후 코스 저장이 실패해도 비싼 API 조회 결과는 남기도록 바로 커밋합니다.
        self.db.commit()


def get_travel_service(db: Session = Depends(get_db)) -> Generator[TravelService, None, None]:
    """FastAPI 의존성. 테스트에서는 이 함수를 교체합니다."""
    if settings.tmap_app_key:
        with httpx.Client(timeout=5.0) as client:
            yield TravelService(
                db,
                TmapTransitClient(client, settings.tmap_app_key),
                TmapPedestrianClient(client, settings.tmap_app_key),
            )
    else:
        yield TravelService(db, None)

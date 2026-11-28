from datetime import datetime

import httpx
import pytest
from sqlalchemy import func, select

from app.models import TravelTimeCache
from app.services.travel import (
    Leg,
    Point,
    TmapError,
    TmapTransitClient,
    TravelService,
    cache_key,
    estimate_leg,
    parse_tmap_transit,
)

A = Point(37.5663, 126.9779)
B = Point(37.5796, 126.9770)  # 약 1.5km
C = Point(37.5446, 127.0557)  # 약 7km
WHEN = datetime(2026, 12, 5, 10, 0)

SAMPLE = {
    "metaData": {
        "plan": {
            "itineraries": [
                {"totalTime": 1830, "walkTime": 400, "walkDistance": 520, "fare": {"regular": {"totalFare": 1650}}},
                {"totalTime": 1500, "walkTime": 900, "walkDistance": 1100, "fare": {"regular": {"totalFare": 1400}}},
            ]
        }
    }
}


def test_estimate_same_point_is_zero():
    assert estimate_leg(A, A).travel_min == 0


def test_estimate_short_is_walk_only_long_is_transit():
    short = estimate_leg(A, Point(37.5700, 126.9779))  # 약 400m
    assert short.fare == 0 and short.walk_min == short.travel_min > 0
    long = estimate_leg(A, C)
    assert long.fare > 0 and long.travel_min > short.travel_min


def test_parse_tmap_picks_fastest_itinerary_and_rounds_up():
    leg = parse_tmap_transit(SAMPLE)
    assert leg == Leg(travel_min=25, walk_min=15, walk_m=1100, fare=1400, source="tmap")


def test_parse_tmap_empty_raises():
    with pytest.raises(TmapError):
        parse_tmap_transit({"result": {"status": 11, "message": "출발지/도착지가 가깝습니다"}})


def make_tmap(handler):
    return TmapTransitClient(httpx.Client(transport=httpx.MockTransport(handler)), "key")


def test_service_uses_tmap_then_cache(db_session):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=SAMPLE)

    svc = TravelService(db_session, make_tmap(handler))
    m1 = svc.leg_matrix([A, B], WHEN)
    assert m1[0][1].source == "tmap" and len(calls) == 1  # A→B 한 번만 조회하고 B→A 는 같은 값을 씀
    assert m1[1][0] == m1[0][1]

    m2 = svc.leg_matrix([A, B], WHEN)
    assert len(calls) == 1  # 두 번째는 캐시
    assert m2[0][1].source == "cache" and m2[0][1].travel_min == 25 and m2[1][0].source == "cache"
    assert db_session.scalar(select(func.count()).select_from(TravelTimeCache)) == 1


def test_cache_key_buckets_weekday_and_hour():
    assert cache_key(A, B, datetime(2026, 12, 5, 10)) != cache_key(A, B, datetime(2026, 12, 7, 10))  # 토 vs 월
    assert cache_key(A, B, datetime(2026, 12, 7, 10, 5)) == cache_key(A, B, datetime(2026, 12, 8, 10, 55))


def test_fatal_tmap_error_falls_back_without_hammering(db_session):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401)

    svc = TravelService(db_session, make_tmap(handler))
    m = svc.leg_matrix([A, B, C], WHEN)
    assert len(calls) == 1  # 첫 호출에서 키 문제를 확인하고 중단
    assert all(m[i][j].source == "estimate" for i in range(3) for j in range(3) if i != j)
    assert db_session.scalar(select(func.count()).select_from(TravelTimeCache)) == 0  # 추정값은 캐시 안 함


def test_partial_failure_mixes_tmap_and_estimate(db_session):
    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        if body["endX"] == str(C.lng):
            return httpx.Response(500)
        return httpx.Response(200, json=SAMPLE)

    svc = TravelService(db_session, make_tmap(handler))
    m = svc.leg_matrix([A, B, C], WHEN)
    assert m[0][1].source == "tmap"
    assert m[0][2].source == "estimate"


# ------------------------------------------------------------ 보행자 API / 호출 절약 / 실패 이유

from app.services.travel import TmapPedestrianClient, parse_tmap_pedestrian  # noqa: E402

NEAR = Point(37.5700, 126.9779)  # A 에서 약 400m: 걸어갈 거리
PED_SAMPLE = {"features": [{"properties": {"totalDistance": 612, "totalTime": 541}}, {"properties": {}}]}


def make_walker(handler):
    return TmapPedestrianClient(httpx.Client(transport=httpx.MockTransport(handler)), "key")


def test_parse_pedestrian_uses_first_feature_totals():
    leg = parse_tmap_pedestrian(PED_SAMPLE)
    assert leg == Leg(travel_min=10, walk_min=10, walk_m=612, fare=0, source="tmap")
    with pytest.raises(TmapError):
        parse_tmap_pedestrian({"features": []})


def test_short_legs_use_pedestrian_and_long_legs_use_transit(db_session):
    ped_calls, transit_calls = [], []

    def ped(request: httpx.Request) -> httpx.Response:
        ped_calls.append(request)
        return httpx.Response(200, json=PED_SAMPLE)

    def transit(request: httpx.Request) -> httpx.Response:
        transit_calls.append(request)
        return httpx.Response(200, json=SAMPLE)

    svc = TravelService(db_session, make_tmap(transit), make_walker(ped))
    m = svc.leg_matrix([A, NEAR, C], WHEN)
    assert m[0][1].walk_m == 612 and m[0][1].fare == 0  # 짧은 구간: 보행자 API
    assert m[0][2].fare == 1400  # 먼 구간: 대중교통 API
    assert len(ped_calls) == 1 and len(transit_calls) == 2  # (A,NEAR) / (A,C), (NEAR,C)
    assert svc.issues == []


def test_pedestrian_blocked_does_not_stop_transit_and_reason_is_reported(db_session):
    def ped(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403)

    svc = TravelService(db_session, make_tmap(lambda r: httpx.Response(200, json=SAMPLE)), make_walker(ped))
    m = svc.leg_matrix([A, NEAR, C], WHEN)
    assert m[0][1].source == "estimate"  # 보행자 API 실패 → 추정값
    assert m[0][2].source == "tmap"  # 대중교통은 계속 사용
    assert svc.issues == ["Tmap 보행자 경로: API 키 오류 또는 해당 상품 미신청(403)"]


def test_quota_exceeded_reason_is_reported(db_session):
    svc = TravelService(db_session, make_tmap(lambda r: httpx.Response(429)))
    svc.leg_matrix([A, C], WHEN)
    assert svc.issues == ["Tmap 대중교통: 호출 한도 초과(429)"]


def test_reverse_cache_entry_is_reused(db_session):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, json=SAMPLE)

    svc = TravelService(db_session, make_tmap(handler))
    svc.leg_matrix([B, A], WHEN)  # B→A 방향으로 캐시에 저장
    m = svc.leg_matrix([A, B], WHEN)  # A→B 로 물어도 같은 구간
    assert len(calls) == 1 and m[0][1].source == "cache"

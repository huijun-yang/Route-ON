from datetime import date, datetime

import httpx
import pytest

from app.api.v1.weather import get_weather_client
from app.core.config import Settings, check_production_settings, settings
from app.main import app
from app.services.kakao import KakaoAuthError, get_kakao_client, verify_token_app_id
from app.services.weather import latest_base_time, latlng_to_grid, parse_forecast

API = "/api/v1"

KAKAO_DOCS = {
    "documents": [
        {
            "id": "111",
            "place_name": "성수 카페",
            "address_name": "서울 성동구 성수동",
            "road_address_name": "서울 성동구 아차산로 1",
            "category_name": "음식점 > 카페",
            "x": "127.0557",
            "y": "37.5446",
        },
        {"id": "bad", "place_name": "좌표없음"},  # 형식이 이상한 항목은 건너뜀
        {"id": "222", "place_name": "지번만", "address_name": "서울 어딘가", "x": "127.0", "y": "37.5"},
    ]
}


def use_kakao(handler):
    def dep():
        with httpx.Client(transport=httpx.MockTransport(handler)) as c:
            yield c

    app.dependency_overrides[get_kakao_client] = dep


# ------------------------------------------------------------------ 장소 검색


def test_place_search_maps_results_and_is_not_shadowed_by_place_id_route(client, monkeypatch):
    monkeypatch.setattr(settings, "kakao_rest_api_key", "rest-key")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=KAKAO_DOCS)

    use_kakao(handler)
    r = client.get(f"{API}/places/search", params={"query": "성수 카페", "lat": 37.54, "lng": 127.05, "radius": 2000})
    assert r.status_code == 200, r.text
    assert seen["auth"] == "KakaoAK rest-key"
    assert seen["params"]["x"] == "127.05" and seen["params"]["y"] == "37.54" and seen["params"]["radius"] == "2000"
    body = r.json()
    assert [p["kakao_place_id"] for p in body] == ["111", "222"]
    assert body[0]["address"] == "서울 성동구 아차산로 1" and body[0]["lat"] == 37.5446
    assert body[1]["address"] == "서울 어딘가"
    # 결과는 그대로 POST /places 에 쓸 수 있다
    assert client.post(f"{API}/places", json=body[0]).status_code == 201


def test_place_search_without_key_is_503_and_kakao_failure_is_502(client, monkeypatch):
    monkeypatch.setattr(settings, "kakao_rest_api_key", "")
    assert client.get(f"{API}/places/search", params={"query": "x"}).status_code == 503
    monkeypatch.setattr(settings, "kakao_rest_api_key", "k")
    use_kakao(lambda request: httpx.Response(500))
    assert client.get(f"{API}/places/search", params={"query": "x"}).status_code == 502
    assert client.get(f"{API}/places/search", params={"query": "x", "lat": 37}).status_code == 422


# ------------------------------------------------------------------ 날씨


def test_grid_conversion_matches_known_points():
    assert latlng_to_grid(37.5665, 126.9780) == (60, 127)  # 서울
    assert latlng_to_grid(35.1796, 129.0756) == (98, 76)  # 부산


def test_latest_base_time():
    assert latest_base_time(datetime(2026, 11, 28, 14, 5)) == ("20261128", "1100")  # 14시 발표는 14:10 부터
    assert latest_base_time(datetime(2026, 11, 28, 14, 10)) == ("20261128", "1400")
    assert latest_base_time(datetime(2026, 11, 28, 1, 0)) == ("20261127", "2300")


def forecast_items():
    rows = []
    for hour, tmp, sky, pty, pop in (("0900", "10", "1", "0", "10"), ("1500", "15", "4", "1", "70")):
        for cat, val in (("TMP", tmp), ("SKY", sky), ("PTY", pty), ("POP", pop)):
            rows.append({"fcstDate": "20261129", "fcstTime": hour, "category": cat, "fcstValue": val})
    return rows


def test_parse_forecast_picks_nearest_hour_and_out_of_range():
    info = parse_forecast(forecast_items(), date(2026, 11, 29), 14)
    assert info.available and info.temp_c == 15 and info.precipitation == "비" and info.pop == 70
    assert info.summary == "비 · 15°C · 강수확률 70%"
    morning = parse_forecast(forecast_items(), date(2026, 11, 29), 8)
    assert morning.sky == "맑음" and morning.summary == "맑음 · 10°C · 강수확률 10%"
    far = parse_forecast(forecast_items(), date(2026, 12, 25), 12)
    assert far.available is False and far.reason == "forecast_out_of_range"


def use_weather(handler):
    def dep():
        with httpx.Client(transport=httpx.MockTransport(handler)) as c:
            yield c

    app.dependency_overrides[get_weather_client] = dep


def test_weather_endpoint(client, monkeypatch):
    monkeypatch.setattr(settings, "kma_api_key", "kma")
    payload = {"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": forecast_items()}}}}
    use_weather(lambda request: httpx.Response(200, json=payload))
    r = client.get(f"{API}/weather", params={"lat": 37.5665, "lng": 126.978, "date": "2026-11-29", "hour": 15})
    assert r.status_code == 200, r.text
    assert r.json()["summary"] == "비 · 15°C · 강수확률 70%" and r.json()["grid"] == [60, 127]

    far = client.get(f"{API}/weather", params={"lat": 37.5, "lng": 127, "date": "2027-01-01"}).json()
    assert far["available"] is False

    # 키 오류 시 KMA 는 JSON 이 아닌 XML 을 돌려줄 수 있다
    use_weather(lambda request: httpx.Response(200, text="<OpenAPI_ServiceResponse/>"))
    assert client.get(f"{API}/weather", params={"lat": 37.5, "lng": 127}).status_code == 502
    monkeypatch.setattr(settings, "kma_api_key", "")
    assert client.get(f"{API}/weather", params={"lat": 37.5, "lng": 127}).status_code == 503


# ------------------------------------------------------------------ 인증 보강


def test_patch_me_updates_nickname(client):
    r = client.patch(f"{API}/auth/me", json={"nickname": "  새닉네임 "})
    assert r.status_code == 200 and r.json()["nickname"] == "새닉네임"
    assert client.patch(f"{API}/auth/me", json={"nickname": "   "}).status_code == 422


def make_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_kakao_app_id_verification():
    ok = make_client(lambda r: httpx.Response(200, json={"id": 1, "app_id": 1234}))
    verify_token_app_id("tok", ok, "1234")  # 통과
    verify_token_app_id("tok", ok, "")  # 설정 안 했으면 검사 생략
    with pytest.raises(KakaoAuthError):
        verify_token_app_id("tok", ok, "9999")
    rejected = make_client(lambda r: httpx.Response(401))
    with pytest.raises(KakaoAuthError):
        verify_token_app_id("tok", rejected, "1234")


def test_production_requires_custom_jwt_secret():
    with pytest.raises(RuntimeError):
        check_production_settings(Settings(app_env="production", jwt_secret_key="change-me-in-env"))
    check_production_settings(Settings(app_env="production", jwt_secret_key="a-real-secret"))
    check_production_settings(Settings(app_env="development"))


def test_cors_origins_parse():
    s = Settings(cors_origins="http://a.com, http://b.com ,")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]

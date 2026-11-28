"""프론트엔드(frontend/src)가 실제로 보내는 요청 형태로 한 흐름을 끝까지 돌려, 서버와 계약이 맞는지 확인합니다."""
from tests.conftest import as_user

API = "/api/v1"
BOB = as_user("bob")

# frontend/src/api/placesApi.js 의 createPlace 가 보내는 형태 (address 가 빈 문자열, category 가 null 일 수 있음)
PLACE = {
    "kakao_place_id": "fe1",
    "name": "프론트 카페",
    "address": "",
    "lat": 37.5446,
    "lng": 127.0557,
    "category": None,
}
PLACE2 = {**PLACE, "kakao_place_id": "fe2", "name": "프론트 전시", "category": "문화,예술 > 박물관", "lat": 37.5796, "lng": 126.9770}


def test_course_flow_with_frontend_payloads(client):
    # 1) 장소 저장 + 추천 체류시간 (PlaceStep/addPlace)
    for p in (PLACE, PLACE2):
        assert client.post(f"{API}/places", json=p).status_code in (200, 201)
    rec = client.get(f"{API}/places/fe2/recommended-stay").json()
    assert rec["recommended_stay_min"] == 120

    # 2) 영업시간 저장: 일반(휴식 없음), 휴무 (PlaceStep/handleSaveHours)
    r = client.post(
        f"{API}/places/fe1/business-hours",
        json={"is_closed": False, "open_time": "10:00", "close_time": "22:00", "break_start": None, "break_end": None, "weekday": 5},
    )
    assert r.status_code == 201, r.text
    r = client.post(f"{API}/places/fe2/business-hours", json={"is_closed": True, "weekday": 0})
    assert r.status_code == 201, r.text
    # 날짜 하루만 적용
    r = client.post(
        f"{API}/places/fe1/business-hours/exceptions",
        json={"is_closed": False, "open_time": "11:00", "close_time": "20:00", "break_start": None, "break_end": None, "date": "2026-12-12"},
    )
    assert r.status_code == 201, r.text

    # 3) 저장된 영업시간 다시 읽기: 서버 시간은 "HH:MM:SS" 형태 (프론트가 slice(0,5) 로 자름)
    rows = client.get(f"{API}/places/fe1/business-hours").json()
    assert rows[0]["open_time"].startswith("10:00") and rows[0]["is_closed"] is False

    # 4) 코스 생성 (LoadingStep): stay_min 은 비우고, title 도 비움
    body = {
        "course_date": "2026-12-05",  # 토요일 = weekday 5
        "start": {"lat": 37.5663, "lng": 126.9779},
        "start_time": "10:00",
        "stops": [
            {"place_id": "fe1", "estimated_cost": 0},
            {"place_id": "fe2", "estimated_cost": 15000},
        ],
    }
    r = client.post(f"{API}/courses", json=body)
    assert r.status_code == 201, r.text
    plan = r.json()
    assert [c["priority_type"] for c in plan["courses"]] == ["time", "walk", "cost"]
    active = next(c for c in plan["courses"] if c["is_active"])

    # 결과 화면(PriorityView/Timeline/WeatherFatigue)이 읽는 필드가 모두 있는지
    for c in plan["courses"]:
        for key in ("priority_label", "total_time", "total_walk", "total_cost", "fatigue_level", "fatigue_score",
                    "total_travel_min", "course_date", "share_uuid", "has_estimated_travel", "start_min"):
            assert key in c, key
    stop = active["stops"][0]
    for key in ("start_time", "departure_time", "arrival_day_offset", "stay_duration", "travel_min", "walk_min",
                "walk_m", "fare", "wait_min", "estimated_cost", "travel_source", "hours", "place"):
        assert key in stop, key
    # stay_min 을 비웠으므로 장소 유형별 추천값(카페 60분, 박물관 120분)이 쓰여야 함
    stay_by_place = {s["place"]["kakao_place_id"]: s["stay_duration"] for s in active["stops"]}
    assert stay_by_place == {"fe1": 60, "fe2": 120}

    # 5) 우선순위 선택 저장
    other = next(c for c in plan["courses"] if not c["is_active"])
    assert client.post(f"{API}/courses/{other['id']}/activate").status_code == 200

    # 6) "30분 더 머무르기" (ResultStep/handleExtend): 첫 장소 도착 시각, 그 장소 위치에서
    first = other["stops"][0]
    r = client.post(
        f"{API}/courses/{other['id']}/replan",
        json={
            "current_time": f"{(first['arrival_min'] % 1440) // 60:02d}:{first['arrival_min'] % 60:02d}",
            "current_lat": first["place"]["lat"],
            "current_lng": first["place"]["lng"],
            "visited_place_ids": [],
            "stay_adjustments": {first["place"]["kakao_place_id"]: 30},
        },
    )
    assert r.status_code == 201, r.text

    # 7) 히스토리 / 공유 보기 (CourseHistory, CourseViewPage)
    summary = client.get(f"{API}/courses?only_active=true").json()
    assert {"id", "title", "course_date", "total_time", "total_cost", "stop_count", "status", "place_names", "group_id"} <= set(summary[0])
    shared = client.get(f"{API}/courses/shared/{active['share_uuid']}")
    assert shared.status_code == 200
    assert client.delete(f"{API}/courses/{active['id']}").status_code == 204


def test_all_closed_error_has_excluded_for_alert(client):
    """LoadingStep 이 alert 에 쓰는 error.detail.excluded 형태."""
    client.post(f"{API}/places", json=PLACE)
    client.post(f"{API}/places/fe1/business-hours", json={"is_closed": True, "weekday": 5})
    r = client.post(
        f"{API}/courses",
        json={
            "course_date": "2026-12-05",
            "start": {"lat": 37.5, "lng": 127.0},
            "start_time": "10:00",
            "stops": [{"place_id": "fe1", "estimated_cost": 0}],
        },
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["message"] and detail["excluded"][0]["reason"] == "CLOSED_ON_DAY"
    assert detail["excluded"][0]["name"] == "프론트 카페"


def test_group_flow_with_frontend_payloads(client):
    # GroupCoursesPage: 생성 → 초대코드 참여, GroupVote: 장소 저장 → 후보 → 투표 → 확정
    g = client.post(f"{API}/groups", json={"title": None}).json()
    assert client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"]}, headers=BOB).status_code == 200

    for p in (PLACE, PLACE2):
        client.post(f"{API}/places", json=p)
        r = client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": p["kakao_place_id"]}, headers=BOB)
        assert r.status_code == 201, r.text
    cand = r.json()["candidates"]
    assert {"id", "place", "vote_count", "voted_by_me", "added_by_nickname"} <= set(cand[0])

    for c in cand:
        assert client.post(f"{API}/groups/{g['id']}/candidates/{c['id']}/vote").status_code == 200
    # 멤버는 확정할 수 없음
    body = {"course_date": "2026-12-05", "start": {"lat": 37.5663, "lng": 126.9779}, "start_time": "10:00", "max_places": 5}
    assert client.post(f"{API}/groups/{g['id']}/finalize", json=body, headers=BOB).status_code == 403
    r = client.post(f"{API}/groups/{g['id']}/finalize", json=body)
    assert r.status_code == 201, r.text
    active = next(c for c in r.json()["courses"] if c["is_active"])
    # 멤버(bob)도 확정된 코스를 볼 수 있어야 함 (CourseViewPage 의 /courses/{id} 폴백)
    assert client.get(f"{API}/courses/{active['id']}", headers=BOB).status_code == 200
    detail = client.get(f"{API}/groups/{g['id']}").json()
    assert detail["status"] == "closed" and detail["course_id"] == active["id"]

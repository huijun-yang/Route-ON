from tests.conftest import as_user, course_body

API = "/api/v1"


def create(client, saved_places, **kw):
    r = client.post(f"{API}/courses", json=course_body(**kw))
    assert r.status_code == 201, r.text
    return r.json()


def test_create_returns_three_versions_with_one_active(client, saved_places):
    data = create(client, saved_places)
    courses = data["courses"]
    assert [c["priority_type"] for c in courses] == ["time", "walk", "cost"]
    assert sum(c["is_active"] for c in courses) == 1 and courses[0]["is_active"]
    assert len({c["group_id"] for c in courses}) == 1 == len({data["group_id"]})
    for c in courses:
        assert c["status"] == "OK"
        assert [s["visit_order"] for s in c["stops"]] == [1, 2, 3]
        assert {s["place"]["kakao_place_id"] for s in c["stops"]} == {"p1", "p2", "p4"}
        assert c["total_time"] == c["end_min"] - c["start_min"] > 0
        assert c["fatigue_level"] in ("여유로움", "보통", "높음")


def test_stop_times_are_consistent(client, saved_places):
    course = create(client, saved_places)["courses"][0]
    prev_departure = course["start_min"]
    for s in course["stops"]:
        assert s["arrival_min"] == prev_departure + s["travel_min"]
        assert s["start_min"] == s["arrival_min"] + s["wait_min"]
        assert s["departure_min"] == s["start_min"] + s["stay_duration"]
        assert s["arrival_time"] and s["departure_time"]
        prev_departure = s["departure_min"]
    assert course["end_min"] == prev_departure


def test_missing_hours_are_assumed_and_warned(client, saved_places):
    data = create(client, saved_places)
    assert any("24시간" in w for w in data["warnings"])
    assert all(s["hours"]["source"] == "assumed" for s in data["courses"][0]["stops"])


def test_saved_hours_are_used_for_the_course_weekday(client, saved_places):
    # 2026-12-05 는 토요일(weekday=5). 경복궁은 토요일 12:00~18:00 만 열림.
    r = client.post(
        f"{API}/places/p2/business-hours",
        json={"weekday": 5, "open_time": "12:00", "close_time": "18:00"},
    )
    assert r.status_code == 201
    course = create(client, saved_places)["courses"][0]
    by_place = {s["place"]["kakao_place_id"]: s for s in course["stops"]}
    assert by_place["p2"]["hours"]["source"] == "saved"
    assert by_place["p2"]["start_min"] >= 12 * 60
    assert by_place["p2"]["departure_min"] <= 18 * 60


def test_inline_hours_override_saved(client, saved_places):
    client.post(f"{API}/places/p2/business-hours", json={"weekday": 5, "open_time": "09:00", "close_time": "10:00"})
    body = course_body(stop_ids=("p2",))
    body["stops"][0]["hours"] = {"open_time": "11:00", "close_time": "20:00"}
    course = client.post(f"{API}/courses", json=body).json()["courses"][0]
    assert course["stops"][0]["hours"]["source"] == "inline"
    assert course["stops"][0]["start_min"] >= 11 * 60


def test_excluded_place_gives_partial_status(client, saved_places):
    body = course_body(stop_ids=("p1", "p2"))
    # p2 는 오전에 끝나서 10시 출발로는 갈 수 없음
    body["stops"][1]["hours"] = {"open_time": "08:00", "close_time": "09:00"}
    data = client.post(f"{API}/courses", json=body).json()
    c = data["courses"][0]
    assert c["status"] == "PARTIAL"
    assert [s["place"]["kakao_place_id"] for s in c["stops"]] == ["p1"]
    assert c["excluded"] == [{"place_id": "p2", "name": "경복궁", "reason": "ALREADY_CLOSED"}]


def test_nothing_feasible_returns_422_and_saves_nothing(client, saved_places):
    body = course_body(stop_ids=("p1",))
    body["stops"][0]["hours"] = {"open_time": "08:00", "close_time": "09:00"}
    r = client.post(f"{API}/courses", json=body)
    assert r.status_code == 422
    assert r.json()["detail"]["excluded"][0]["reason"] == "ALREADY_CLOSED"
    assert client.get(f"{API}/courses", params={"only_active": "false"}).json() == []


def test_past_midnight_times_are_kept_not_truncated(client, saved_places):
    body = course_body(stop_ids=("p1",), start_time="23:00")
    body["stops"][0]["stay_min"] = 90
    body["stops"][0]["hours"] = {"open_time": "18:00", "close_time": "03:00"}  # 심야 영업
    c = client.post(f"{API}/courses", json=body).json()["courses"][0]
    stop = c["stops"][0]
    assert stop["departure_min"] >= 1440  # 자정 이후
    assert stop["departure_day_offset"] == 1
    assert stop["departure_time"] == f"{(stop['departure_min'] % 1440) // 60:02d}:{stop['departure_min'] % 60:02d}"
    assert c["end_day_offset"] == 1


def test_unknown_place_is_404(client, saved_places):
    r = client.post(f"{API}/courses", json=course_body(stop_ids=("p1", "nope")))
    assert r.status_code == 404
    assert r.json()["detail"]["missing_place_ids"] == ["nope"]


def test_validation_rejects_duplicates_and_too_many(client, saved_places):
    assert client.post(f"{API}/courses", json=course_body(stop_ids=("p1", "p1"))).status_code == 422
    assert client.post(f"{API}/courses", json=course_body(stop_ids=tuple(f"x{i}" for i in range(9)))).status_code == 422


def test_list_get_group_shared(client, saved_places):
    data = create(client, saved_places)
    cid = data["courses"][0]["id"]

    listed = client.get(f"{API}/courses").json()
    assert len(listed) == 1 and listed[0]["id"] == cid and listed[0]["place_names"]
    assert len(client.get(f"{API}/courses", params={"only_active": "false"}).json()) == 3

    assert client.get(f"{API}/courses/{cid}").json()["id"] == cid
    grp = client.get(f"{API}/courses/groups/{data['group_id']}").json()
    assert [c["priority_type"] for c in grp["courses"]] == ["time", "walk", "cost"]

    share = data["courses"][0]["share_uuid"]
    shared = client.get(f"{API}/courses/shared/{share}", headers={"X-Test-User": "nobody"})  # 로그인 없이
    assert shared.status_code == 200 and "owner_user_id" not in shared.json()


def test_other_users_cannot_see_or_change(client, saved_places):
    cid = create(client, saved_places)["courses"][0]["id"]
    h = as_user("bob")
    assert client.get(f"{API}/courses/{cid}", headers=h).status_code == 404
    assert client.patch(f"{API}/courses/{cid}", json={"title": "x"}, headers=h).status_code == 404
    assert client.delete(f"{API}/courses/{cid}", headers=h).status_code == 404
    assert client.post(f"{API}/courses/{cid}/activate", headers=h).status_code == 404
    assert client.get(f"{API}/courses", headers=h).json() == []


def test_activate_switches_active_version(client, saved_places):
    data = create(client, saved_places)
    walk = data["courses"][1]
    r = client.post(f"{API}/courses/{walk['id']}/activate")
    assert r.status_code == 200 and r.json()["is_active"] is True
    grp = client.get(f"{API}/courses/groups/{data['group_id']}").json()["courses"]
    assert [c["is_active"] for c in grp] == [False, True, False]
    assert [c["id"] for c in client.get(f"{API}/courses").json()] == [walk["id"]]


def test_rename_and_delete_removes_whole_set(client, saved_places):
    data = create(client, saved_places)
    cid = data["courses"][0]["id"]
    assert client.patch(f"{API}/courses/{cid}", json={"title": "새 이름"}).json()["title"] == "새 이름"
    assert client.delete(f"{API}/courses/{cid}").status_code == 204
    assert client.get(f"{API}/courses", params={"only_active": "false"}).json() == []
    assert client.get(f"{API}/courses/{cid}").status_code == 404


def test_replan_extends_stay_and_skips_visited(client, saved_places):
    first = create(client, saved_places)["courses"][0]
    p1_stop = next(s for s in first["stops"] if s["place"]["kakao_place_id"] == "p1")
    body = {
        "current_time": "11:30",
        "current_lat": 37.5663,
        "current_lng": 126.9779,
        "visited_place_ids": ["p2"],
        "stay_adjustments": {"p1": 30},
    }
    r = client.post(f"{API}/courses/{first['id']}/replan", json=body)
    assert r.status_code == 201, r.text
    new = r.json()["courses"][0]
    ids = {s["place"]["kakao_place_id"] for s in new["stops"]}
    assert ids == {"p1", "p4"}  # p2 는 방문 완료로 제외
    new_p1 = next(s for s in new["stops"] if s["place"]["kakao_place_id"] == "p1")
    assert new_p1["stay_duration"] == p1_stop["stay_duration"] + 30
    assert new["start_min"] == 11 * 60 + 30
    # 내 코스는 새로 만들지 않고 같은 코스를 덮어써서 갱신합니다. (ID, 그룹, 공유 링크 유지)
    assert new["id"] == first["id"] and new["group_id"] == first["group_id"]
    assert new["share_uuid"] == first["share_uuid"]
    assert [c["id"] for c in r.json()["courses"]] == [c["id"] for c in client.get(
        f"{API}/courses/groups/{first['group_id']}").json()["courses"]]
    # 히스토리에 항목이 늘지 않고, 저장된 코스도 갱신된 내용입니다.
    history = client.get(f"{API}/courses", params={"only_active": "false"}).json()
    assert len(history) == 3
    saved = client.get(f"{API}/courses/{first['id']}").json()
    assert {s["place"]["kakao_place_id"] for s in saved["stops"]} == {"p1", "p4"}
    assert saved["start_min"] == 11 * 60 + 30


def test_replan_twice_keeps_one_history_entry_and_active_choice(client, saved_places):
    plan = create(client, saved_places)
    active_before = next(c for c in plan["courses"] if c["is_active"])["id"]
    body = {"current_time": "11:00", "current_lat": 37.5663, "current_lng": 126.9779}
    for _ in range(2):
        r = client.post(f"{API}/courses/{plan['courses'][0]['id']}/replan", json=body)
        assert r.status_code == 201, r.text
    assert next(c for c in r.json()["courses"] if c["is_active"])["id"] == active_before
    assert len(client.get(f"{API}/courses", params={"only_active": "false"}).json()) == 3


def test_replan_by_non_owner_creates_own_copy(client, saved_places):
    # 내 코스가 아닌 코스(그룹 멤버로 열람)는 원본을 건드리지 않고 내 새 코스를 만듭니다.
    g = client.post(f"{API}/groups", json={"title": "t"}).json()
    client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"]}, headers=as_user("bob"))
    for pid in ("p1", "p2"):
        r = client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": pid})
        cand = [c for c in r.json()["candidates"] if c["place"]["kakao_place_id"] == pid][0]
        client.post(f"{API}/groups/{g['id']}/candidates/{cand['id']}/vote")
    fin = client.post(
        f"{API}/groups/{g['id']}/finalize",
        json={"course_date": "2026-12-05", "start": {"lat": 37.5547, "lng": 126.9707}, "start_time": "10:00"},
    )
    original = fin.json()["courses"][0]
    r = client.post(
        f"{API}/courses/{original['id']}/replan",
        json={"current_time": "11:00", "current_lat": 37.5663, "current_lng": 126.9779},
        headers=as_user("bob"),
    )
    assert r.status_code == 201, r.text
    mine = r.json()["courses"][0]
    assert mine["id"] != original["id"] and mine["group_id"] != original["group_id"]
    # 원본은 그대로
    assert client.get(f"{API}/courses/{original['id']}").json()["start_min"] == original["start_min"]


def test_replan_with_nothing_left_is_422(client, saved_places):
    first = create(client, saved_places, stop_ids=("p1",))["courses"][0]
    r = client.post(
        f"{API}/courses/{first['id']}/replan",
        json={"current_time": "12:00", "current_lat": 37.5, "current_lng": 127.0, "visited_place_ids": ["p1"]},
    )
    assert r.status_code == 422


def test_closed_day_place_is_excluded(client, saved_places):
    # 2026-12-05 는 토요일(weekday=5). 경복궁(p2)은 토요일 휴무.
    r = client.post(f"{API}/places/p2/business-hours", json={"weekday": 5, "is_closed": True})
    assert r.status_code == 201, r.text
    assert r.json()["is_closed"] is True and r.json()["open_time"] is None

    data = create(client, saved_places)
    assert any("휴무" in w for w in data["warnings"])
    for c in data["courses"]:
        assert c["status"] == "PARTIAL"
        assert {s["place"]["kakao_place_id"] for s in c["stops"]} == {"p1", "p4"}
        assert {"place_id": "p2", "name": c["excluded"][0]["name"], "reason": "CLOSED_ON_DAY"} in c["excluded"]


def test_all_places_closed_returns_422(client, saved_places):
    body = course_body(stop_ids=("p2",))
    body["stops"][0]["hours"] = {"is_closed": True}
    r = client.post(f"{API}/courses", json=body)
    assert r.status_code == 422
    assert "CLOSED_ON_DAY" in r.text


def test_closed_hours_reject_times_and_open_requires_times(client, saved_places):
    r = client.post(f"{API}/places/p2/business-hours", json={"weekday": 1, "is_closed": True, "open_time": "09:00"})
    assert r.status_code == 422
    r = client.post(f"{API}/places/p2/business-hours", json={"weekday": 1})
    assert r.status_code == 422


def test_estimated_travel_is_persisted_and_visible_on_reload(client, saved_places):
    # 테스트 환경은 Tmap 이 없어 추정값만 쓰므로 저장된 코스를 다시 조회해도 표시되어야 합니다.
    created = create(client, saved_places)["courses"][0]
    r = client.get(f"{API}/courses/{created['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["has_estimated_travel"] is True
    assert {s["travel_source"] for s in data["stops"]} == {"estimate"}


def test_stay_defaults_to_category_recommendation(client, saved_places):
    body = course_body(stop_ids=("p3",))  # 카페
    del body["stops"][0]["stay_min"]
    r = client.post(f"{API}/courses", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["courses"][0]["stops"][0]["stay_duration"] == 60

    body = course_body(stop_ids=("p2",))  # 관광
    del body["stops"][0]["stay_min"]
    r = client.post(f"{API}/courses", json=body)
    assert r.json()["courses"][0]["stops"][0]["stay_duration"] == 90


def test_explicit_stay_wins_and_recommended_stay_endpoint(client, saved_places):
    body = course_body(stop_ids=("p2",))
    body["stops"][0]["stay_min"] = 45
    r = client.post(f"{API}/courses", json=body)
    assert r.json()["courses"][0]["stops"][0]["stay_duration"] == 45
    r = client.get(f"{API}/places/p2/recommended-stay")
    assert r.status_code == 200 and r.json()["recommended_stay_min"] == 90


def test_recommend_stay_rules():
    from app.services.stay_time import recommend_stay

    assert recommend_stay("음식점 > 카페 > 커피전문점") == 60
    assert recommend_stay("문화,예술 > 박물관") == 120
    assert recommend_stay("음식점 > 한식") == 80
    assert recommend_stay(None) == 60
    assert recommend_stay("알 수 없음") == 60


def test_date_exception_overrides_weekday_hours(client, saved_places):
    # 요일 규칙은 12~18시, 그러나 2026-12-05 하루만 별도 규칙.
    client.post(f"{API}/places/p2/business-hours", json={"weekday": 5, "open_time": "12:00", "close_time": "18:00"})
    r = client.post(f"{API}/places/p2/business-hours/exceptions", json={"date": "2026-12-05", "is_closed": True})
    assert r.status_code == 201, r.text
    # 같은 날짜 재저장은 수정(200)
    r = client.post(
        f"{API}/places/p2/business-hours/exceptions",
        json={"date": "2026-12-05", "open_time": "14:00", "close_time": "16:00"},
    )
    assert r.status_code == 200
    course = create(client, saved_places)["courses"][0]
    p2 = {s["place"]["kakao_place_id"]: s for s in course["stops"]}["p2"]
    assert p2["hours"]["source"] == "exception"
    assert p2["start_min"] >= 14 * 60 and p2["departure_min"] <= 16 * 60

    # 예외를 임시휴무로 바꾸면 제외됨
    client.post(f"{API}/places/p2/business-hours/exceptions", json={"date": "2026-12-05", "is_closed": True})
    data = create(client, saved_places)
    assert all(c["excluded"][0]["reason"] == "CLOSED_ON_DAY" for c in data["courses"])

    # 삭제하면 요일 규칙으로 복귀
    assert client.delete(f"{API}/places/p2/business-hours/exceptions/2026-12-05").status_code == 204
    course = create(client, saved_places)["courses"][0]
    assert {s["place"]["kakao_place_id"]: s for s in course["stops"]}["p2"]["hours"]["source"] == "saved"


def test_date_exception_list_validation_and_other_dates_unaffected(client, saved_places):
    assert client.post(f"{API}/places/p2/business-hours/exceptions", json={"date": "2026-12-05"}).status_code == 422
    client.post(f"{API}/places/p2/business-hours/exceptions", json={"date": "2026-12-12", "is_closed": True})
    client.post(f"{API}/places/p2/business-hours/exceptions", json={"date": "2026-12-06", "is_closed": True})
    rows = client.get(f"{API}/places/p2/business-hours/exceptions").json()
    assert [r["date"] for r in rows] == ["2026-12-06", "2026-12-12"]
    rows = client.get(f"{API}/places/p2/business-hours/exceptions?from_date=2026-12-10").json()
    assert [r["date"] for r in rows] == ["2026-12-12"]
    # 12-05 코스는 영향 없음
    assert all(s["hours"]["source"] == "assumed" for s in create(client, saved_places)["courses"][0]["stops"])
    assert client.delete(f"{API}/places/p2/business-hours/exceptions/2030-01-01").status_code == 404


def test_replan_retries_previously_excluded_places(client, saved_places):
    # p2 는 09:00~14:00, 체류 60분 → 13:30 출발이면 이미 늦어서 제외됨
    body = course_body(stop_ids=("p1", "p2"), start_time="13:30")
    body["stops"][1]["hours"] = {"open_time": "09:00", "close_time": "14:00"}
    first = client.post(f"{API}/courses", json=body).json()["courses"][0]
    assert [e["place_id"] for e in first["excluded"]] == ["p2"]

    # 10:00 로 재계획하면 p2 도 다시 후보가 되어 방문 가능
    r = client.post(
        f"{API}/courses/{first['id']}/replan",
        json={"current_time": "10:00", "current_lat": 37.5663, "current_lng": 126.9779},
    )
    assert r.status_code == 201, r.text
    new = r.json()["courses"][0]
    assert {s["place"]["kakao_place_id"] for s in new["stops"]} == {"p1", "p2"}
    assert new["excluded"] in (None, [])


def test_replan_keeps_closed_place_excluded(client, saved_places):
    client.post(f"{API}/places/p2/business-hours", json={"weekday": 5, "is_closed": True})
    first = create(client, saved_places)["courses"][0]
    r = client.post(
        f"{API}/courses/{first['id']}/replan",
        json={"current_time": "10:30", "current_lat": 37.5663, "current_lng": 126.9779},
    )
    assert r.status_code == 201, r.text
    new = r.json()["courses"][0]
    assert {s["place"]["kakao_place_id"] for s in new["stops"]} == {"p1", "p4"}
    assert [e["reason"] for e in new["excluded"]] == ["CLOSED_ON_DAY"]

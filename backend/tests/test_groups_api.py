from tests.conftest import as_user

API = "/api/v1"
ALICE, BOB, CAROL = as_user("alice"), as_user("bob"), as_user("carol")


def make_group(client, title="성수 모임"):
    r = client.post(f"{API}/groups", json={"title": title}, headers=ALICE)
    assert r.status_code == 201, r.text
    return r.json()


def candidate_ids(group):
    return {c["place"]["kakao_place_id"]: c["id"] for c in group["candidates"]}


def test_create_returns_owner_and_invite_code(client):
    g = make_group(client)
    assert g["status"] == "open" and g["my_role"] == "owner" and len(g["invite_code"]) == 8
    assert [(m["nickname"], m["role"]) for m in g["members"]] == [("alice", "owner")]


def test_join_with_code_is_idempotent_and_case_insensitive(client):
    g = make_group(client)
    r = client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"].lower()}, headers=BOB)
    assert r.status_code == 200 and r.json()["my_role"] == "member"
    again = client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"]}, headers=BOB)
    assert len(again.json()["members"]) == 2
    assert client.post(f"{API}/groups/join", json={"invite_code": "ZZZZZZZZ"}, headers=BOB).status_code == 404


def test_non_member_cannot_see_group(client):
    g = make_group(client)
    assert client.get(f"{API}/groups/{g['id']}", headers=CAROL).status_code == 404
    assert client.get(f"{API}/groups", headers=CAROL).json() == []
    assert len(client.get(f"{API}/groups", headers=ALICE).json()) == 1


def test_candidates_and_votes(client, saved_places):
    g = make_group(client)
    client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"]}, headers=BOB)

    r = client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p1"}, headers=BOB)
    assert r.status_code == 201
    assert client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p1"}, headers=ALICE).status_code == 409
    assert client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "nope"}, headers=ALICE).status_code == 404
    client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p2"}, headers=ALICE)
    ids = candidate_ids(client.get(f"{API}/groups/{g['id']}", headers=ALICE).json())

    # 중복 투표는 한 표로만 센다
    for _ in range(2):
        client.post(f"{API}/groups/{g['id']}/candidates/{ids['p1']}/vote", headers=ALICE)
    client.post(f"{API}/groups/{g['id']}/candidates/{ids['p1']}/vote", headers=BOB)
    detail = client.get(f"{API}/groups/{g['id']}", headers=ALICE).json()
    p1 = next(c for c in detail["candidates"] if c["place"]["kakao_place_id"] == "p1")
    assert p1["vote_count"] == 2 and p1["voted_by_me"] is True
    assert detail["candidates"][0]["place"]["kakao_place_id"] == "p1"  # 득표순 정렬
    assert p1["added_by_nickname"] == "bob"

    after = client.delete(f"{API}/groups/{g['id']}/candidates/{ids['p1']}/vote", headers=ALICE).json()
    p1 = next(c for c in after["candidates"] if c["place"]["kakao_place_id"] == "p1")
    assert p1["vote_count"] == 1 and p1["voted_by_me"] is False


def test_only_adder_or_owner_can_remove_candidate(client, saved_places):
    g = make_group(client)
    for h in (BOB, CAROL):
        client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"]}, headers=h)
    client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p1"}, headers=BOB)
    cid = candidate_ids(client.get(f"{API}/groups/{g['id']}", headers=BOB).json())["p1"]
    assert client.delete(f"{API}/groups/{g['id']}/candidates/{cid}", headers=CAROL).status_code == 403
    assert client.delete(f"{API}/groups/{g['id']}/candidates/{cid}", headers=ALICE).status_code == 200


def finalize_body(**kw):
    body = {
        "course_date": "2026-12-05",
        "start": {"lat": 37.5547, "lng": 126.9707},
        "start_time": "10:00",
    }
    body.update(kw)
    return body


def test_finalize_builds_course_from_top_voted_and_closes(client, saved_places):
    g = make_group(client)
    client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"]}, headers=BOB)
    for pid in ("p1", "p2", "p3"):
        client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": pid}, headers=ALICE)
    ids = candidate_ids(client.get(f"{API}/groups/{g['id']}", headers=ALICE).json())
    for pid, voters in (("p1", (ALICE, BOB)), ("p2", (BOB,))):  # p3 은 0표
        for h in voters:
            client.post(f"{API}/groups/{g['id']}/candidates/{ids[pid]}/vote", headers=h)

    assert client.post(f"{API}/groups/{g['id']}/finalize", json=finalize_body(), headers=BOB).status_code == 403

    r = client.post(f"{API}/groups/{g['id']}/finalize", json=finalize_body(), headers=ALICE)
    assert r.status_code == 201, r.text
    data = r.json()
    placed = {s["place"]["kakao_place_id"] for s in data["courses"][0]["stops"]}
    assert placed == {"p1", "p2"}

    closed = client.get(f"{API}/groups/{g['id']}", headers=BOB).json()
    assert closed["status"] == "closed" and closed["course_group_id"] == data["group_id"]
    # 멤버(bob)도 코스를 볼 수 있고, 외부인(carol)은 못 본다
    cid = data["courses"][0]["id"]
    assert client.get(f"{API}/courses/{cid}", headers=BOB).status_code == 200
    assert client.get(f"{API}/courses/groups/{data['group_id']}", headers=BOB).status_code == 200
    assert client.get(f"{API}/courses/{cid}", headers=CAROL).status_code == 404

    # 마감 후에는 변경 불가
    assert client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p4"}, headers=ALICE).status_code == 409
    assert client.post(f"{API}/groups/{g['id']}/finalize", json=finalize_body(), headers=ALICE).status_code == 409
    assert client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"]}, headers=CAROL).status_code == 409
    # 그룹에 연결된 코스는 삭제 불가
    assert client.delete(f"{API}/courses/{cid}", headers=ALICE).status_code == 409


def test_finalize_uses_owner_saved_hours(client, saved_places):
    client.post(
        f"{API}/places/p1/business-hours",
        json={"weekday": 5, "open_time": "14:00", "close_time": "20:00"},
        headers=ALICE,
    )
    g = make_group(client)
    client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p1"}, headers=ALICE)
    cid = candidate_ids(client.get(f"{API}/groups/{g['id']}", headers=ALICE).json())["p1"]
    client.post(f"{API}/groups/{g['id']}/candidates/{cid}/vote", headers=ALICE)
    r = client.post(f"{API}/groups/{g['id']}/finalize", json=finalize_body(), headers=ALICE).json()
    stop = r["courses"][0]["stops"][0]
    assert stop["hours"]["source"] == "saved" and stop["start_min"] >= 14 * 60


def test_finalize_without_votes_is_422(client, saved_places):
    g = make_group(client)
    client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p1"}, headers=ALICE)
    assert client.post(f"{API}/groups/{g['id']}/finalize", json=finalize_body(), headers=ALICE).status_code == 422


def test_activate_after_finalize_moves_group_link(client, saved_places):
    g = make_group(client)
    client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p1"}, headers=ALICE)
    cid = candidate_ids(client.get(f"{API}/groups/{g['id']}", headers=ALICE).json())["p1"]
    client.post(f"{API}/groups/{g['id']}/candidates/{cid}/vote", headers=ALICE)
    data = client.post(f"{API}/groups/{g['id']}/finalize", json=finalize_body(), headers=ALICE).json()
    cost = data["courses"][2]
    assert client.post(f"{API}/courses/{cost['id']}/activate", headers=ALICE).status_code == 200
    assert client.get(f"{API}/groups/{g['id']}", headers=ALICE).json()["course_id"] == cost["id"]


def test_leave_and_delete(client, saved_places):
    g = make_group(client)
    client.post(f"{API}/groups/join", json={"invite_code": g["invite_code"]}, headers=BOB)
    assert client.delete(f"{API}/groups/{g['id']}/members/me", headers=ALICE).status_code == 409  # 대표
    assert client.delete(f"{API}/groups/{g['id']}/members/me", headers=BOB).status_code == 204
    assert client.get(f"{API}/groups/{g['id']}", headers=BOB).status_code == 404
    client.post(f"{API}/groups/{g['id']}/candidates", json={"place_id": "p1"}, headers=ALICE)
    assert client.delete(f"{API}/groups/{g['id']}", headers=BOB).status_code == 404
    assert client.delete(f"{API}/groups/{g['id']}", headers=ALICE).status_code == 204
    assert client.get(f"{API}/groups", headers=ALICE).json() == []

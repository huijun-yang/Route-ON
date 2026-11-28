"""API 테스트 공통 설정. SQLite(메모리) + 가짜 외부 API 로 돌아가므로 DB/키가 없어도 됩니다."""
import os

import httpx
import pytest
from fastapi import Depends, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.core.database import get_db
from app.main import app
from app.models import Base, User
from app.services.kakao import get_kakao_client
from app.services.travel import TravelService, get_travel_service


@pytest.fixture()
def db_session():
    """기본은 SQLite(메모리). 실제 PostgreSQL 에서도 돌려보려면 TEST_DATABASE_URL 을 지정하세요.

    예) TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/routeon_test pytest
    (주의: 그 DB 의 테이블을 모두 지우고 다시 만듭니다. 개발용 routeon DB 를 가리키지 마세요.)
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    if url:
        Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def users(db_session):
    made = {}
    for name in ("alice", "bob", "carol"):
        u = User(kakao_id=f"k-{name}", nickname=name)
        db_session.add(u)
        made[name] = u
    db_session.commit()
    return {k: v.id for k, v in made.items()}


@pytest.fixture()
def client(db_session, users):
    """헤더 X-Test-User: alice|bob|carol 로 로그인한 사용자를 바꿉니다. (기본 alice)"""

    def override_db():
        yield db_session

    def override_user(request: Request, db=Depends(get_db)):
        name = request.headers.get("X-Test-User", "alice")
        user = db.get(User, users[name]) if name in users else None
        if user is None:
            raise HTTPException(status_code=401, detail="not authenticated")
        return user

    def override_travel(db=Depends(get_db)):
        yield TravelService(db, None)  # Tmap 없이 추정값만 사용

    def override_kakao():
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        with httpx.Client(transport=httpx.MockTransport(handler)) as c:
            yield c

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_travel_service] = override_travel
    app.dependency_overrides[get_kakao_client] = override_kakao
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def as_user(name: str) -> dict:
    return {"X-Test-User": name}


PLACES = {
    "p1": dict(kakao_place_id="p1", name="서울시청", address="서울 중구", lat=37.5663, lng=126.9779, category="관광"),
    "p2": dict(kakao_place_id="p2", name="경복궁", address="서울 종로구", lat=37.5796, lng=126.9770, category="관광"),
    "p3": dict(kakao_place_id="p3", name="성수 카페", address="서울 성동구", lat=37.5446, lng=127.0557, category="카페"),
    "p4": dict(kakao_place_id="p4", name="남산타워", address="서울 용산구", lat=37.5512, lng=126.9882, category="관광"),
}


@pytest.fixture()
def saved_places(client):
    for p in PLACES.values():
        assert client.post("/api/v1/places", json=p).status_code in (200, 201)
    return PLACES


def course_body(stop_ids=("p1", "p2", "p4"), **overrides):
    body = {
        "title": "테스트 코스",
        "course_date": "2026-12-05",  # 토요일
        "start": {"lat": 37.5547, "lng": 126.9707},
        "start_time": "10:00",
        "stops": [{"place_id": pid, "stay_min": 60} for pid in stop_ids],
    }
    body.update(overrides)
    return body

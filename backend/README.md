# Backend

FastAPI + PostgreSQL/PostGIS 기반 Route-ON API 서버입니다.

## 로컬 실행

```bash
cd backend
python -m venv venv            # Python 3.11 권장
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # 복사 후 값 채우기 (Windows: copy .env.example .env)
docker compose up -d           # PostGIS DB 실행
alembic upgrade head           # 테이블 생성
uvicorn app.main:app --reload  # http://localhost:8000/api/v1/health
```

## 환경변수 규칙

- 설정은 모두 `backend/.env`에 두고, 코드에서는 `app/core/config.py`의 `settings`로만 읽습니다. (`os.environ` 직접 사용 금지)
- 변수명은 **대문자 + 언더스코어**이며, `config.py`의 필드명을 대문자로 바꾼 것과 같아야 합니다. (예: `jwt_secret_key` → `JWT_SECRET_KEY`)
- 새 변수를 추가할 때는 아래 세 곳을 **한 번에** 수정합니다.
  1. `app/core/config.py`
  2. `backend/.env.example` (값은 비우거나 예시값)
  3. 이 문서의 표
- 실제 키와 비밀번호는 `.env`에만 적고 커밋하지 않습니다.

| 변수명 | 용도 | 비고 |
|---|---|---|
| `DATABASE_URL` | PostgreSQL 접속 주소 | 로컬은 docker-compose 기본값 사용 |
| `APP_ENV` | 실행 환경 | `production` 이면 기본 JWT 키로는 서버가 시작되지 않음 |
| `CORS_ORIGINS` | 프론트 주소(쉼표 구분) | 기본: localhost 3000/5173 |
| `JWT_SECRET_KEY` | JWT 서명 키 | 운영 환경에서는 반드시 변경 |
| `JWT_ALGORITHM` | JWT 알고리즘 | 기본 `HS256` |
| `JWT_EXPIRE_MINUTES` | JWT 유효 시간(분) | 기본 `10080`(7일) |
| `KAKAO_REST_API_KEY` | 카카오 로컬(장소 검색) REST API | 없으면 `/places/search` 가 503 |
| `KAKAO_APP_ID` | 카카오 앱 ID | 설정하면 다른 앱의 토큰으로 로그인하는 것을 차단 (선택) |
| `TMAP_APP_KEY` | Tmap 대중교통 + 보행자 경로 API | 없거나 호출이 막히면 직선거리 기반 추정값으로 계산. 두 API 는 상품·한도가 따로라 SK Open API 콘솔에서 앱에 상품을 각각 신청해야 함 |
| `KMA_API_KEY` | 기상청 단기예보 API | 없으면 `/weather` 가 503 |

프론트엔드 변수는 `frontend/.env`에 두며 이름이 `VITE_`로 시작합니다. (`VITE_KAKAO_JAVASCRIPT_KEY`: 카카오 JavaScript 키)

## Swagger 로 API 시험하기

서버를 켠 뒤 http://localhost:8000/docs 에서 API 를 직접 호출해볼 수 있습니다.
로그인이 필요한 API 는 카카오 로그인 없이도 아래 개발용 토큰으로 시험할 수 있습니다. (로컬 개발 전용)

```bash
cd backend
python -m scripts.dev_token   # 'dev-local' 테스트 사용자를 만들고 JWT 를 출력
```

출력된 토큰을 `/docs` 오른쪽 위 **Authorize** 에 붙여넣으면 됩니다.

## API 요약

| 메서드 | 경로 | 설명 | 로그인 |
|---|---|---|---|
| GET | `/api/v1/health`, `/api/v1/health/db` | 서버/DB 상태 확인 | 불필요 |
| POST | `/api/v1/auth/kakao` | 카카오 토큰으로 로그인, JWT 발급 | 불필요 |
| GET | `/api/v1/auth/me` | 내 정보 | 필요 |
| POST | `/api/v1/places` | 장소 저장(이미 있으면 기존 값 유지) | 필요 |
| GET | `/api/v1/places/{place_id}` | 장소 조회 | 불필요 |
| POST | `/api/v1/places/{place_id}/business-hours` | 내 영업시간 저장/수정(요일 단위) | 필요 |
| GET | `/api/v1/places/{place_id}/business-hours` | 내 영업시간 조회 | 필요 |
| DELETE | `/api/v1/places/{place_id}/business-hours/{weekday}` | 내 영업시간 삭제 | 필요 |
| GET | `/api/v1/places/{place_id}/recommended-stay` | 장소 유형별 추천 체류시간(분) | 불필요 |
| POST | `/api/v1/places/{place_id}/business-hours/exceptions` | 특정 날짜 영업시간/임시휴무 저장·수정 (`is_closed`) | 필요 |
| GET | `/api/v1/places/{place_id}/business-hours/exceptions` | 날짜별 예외 조회 (`from_date` 선택) | 필요 |
| DELETE | `/api/v1/places/{place_id}/business-hours/exceptions/{date}` | 날짜별 예외 삭제 | 필요 |
| GET | `/api/v1/places/search?query=` | 카카오 로컬 장소 검색 (`lat`,`lng`,`radius` 선택) | 필요 |
| PATCH | `/api/v1/auth/me` | 닉네임 수정 | 필요 |
| POST | `/api/v1/courses` | 장소 목록으로 코스 3개(시간/도보/비용) 생성·저장 | 필요 |
| GET | `/api/v1/courses` | 내 코스 목록 (`only_active=false` 면 3버전 모두) | 필요 |
| GET | `/api/v1/courses/{id}` | 코스 상세 (주인 또는 그룹 멤버) | 필요 |
| GET | `/api/v1/courses/groups/{group_id}` | 같은 요청의 3개 버전 | 필요 |
| GET | `/api/v1/courses/shared/{share_uuid}` | 공유 링크용 조회 | 불필요 |
| PATCH | `/api/v1/courses/{id}` | 코스 이름 수정 | 필요 |
| POST | `/api/v1/courses/{id}/activate` | 3버전 중 선택 | 필요 |
| POST | `/api/v1/courses/{id}/replan` | 현재 위치·시각 기준 재계획 (예: 30분 더 머무르기). 내 코스는 **같은 코스를 덮어써서 갱신**(ID·공유 링크·히스토리 유지), 남의 코스는 내 새 코스 3개 생성 | 필요 |
| DELETE | `/api/v1/courses/{id}` | 코스 삭제(3버전 묶음 전체) | 필요 |
| POST | `/api/v1/groups` | 그룹 생성 (초대코드 발급) | 필요 |
| POST | `/api/v1/groups/join` | 초대코드로 참여 | 필요 |
| GET | `/api/v1/groups`, `/api/v1/groups/{id}` | 내 그룹 목록 / 상세(후보·득표 포함) | 필요 |
| POST/DELETE | `/api/v1/groups/{id}/candidates[/{cid}]` | 후보 장소 추가 / 삭제 | 필요 |
| POST/DELETE | `/api/v1/groups/{id}/candidates/{cid}/vote` | 투표 / 투표 취소 | 필요 |
| POST | `/api/v1/groups/{id}/finalize` | 득표 상위 장소로 코스 확정 (대표만) | 필요 |
| DELETE | `/api/v1/groups/{id}/members/me`, `/api/v1/groups/{id}` | 그룹 나가기 / 삭제(대표) | 필요 |
| GET | `/api/v1/weather?lat=&lng=&date=&hour=` | 기상청 단기예보 (약 3일 이내) | 필요 |

영업시간은 `(사용자, 장소, 요일)` 단위로 개인 계정에만 저장되며 다른 사용자에게 공유되지 않습니다.
`weekday` 는 0=월 ~ 6=일, `open_time`/`close_time` 이 같으면 24시간 영업, 자정을 넘기는 심야 영업도 허용합니다.
휴무 요일은 `{"weekday": 1, "is_closed": true}` 로 저장하며(시간은 비움), 임시휴무 같은 특정 날짜 예외는 `business-hours/exceptions` 로 저장합니다.

## 코스 생성이 동작하는 방식

1. 요청한 장소들의 **영업시간**을 정합니다. 우선순위: 요청에 직접 넣은 값 > 날짜별 예외(임시휴무 등) > 내가 저장한 값(방문일 요일) > 없으면 24시간 영업 가정(응답 `warnings` 에 표시). 그날 휴무인 장소는 `excluded` 에 `CLOSED_ON_DAY` 로 담기고 나머지로 코스가 만들어집니다(`status=PARTIAL`).
   체류시간(`stay_min`)을 비우면 장소 카테고리별 추천값(`services/stay_time.py`)을 씁니다.
2. **이동시간**은 `services/travel.py` 가 계산합니다. DB 캐시 → Tmap(걸어갈 거리는 보행자 경로, 먼 구간은 대중교통) → (키 없음/실패 시) 직선거리 추정 순서입니다. A→B 와 B→A 는 같은 값으로 보고 한 방향만 조회해 호출 수를 절반으로 줄이며, 실패 이유(한도 초과 등)는 응답 `warnings` 에 함께 표시됩니다.
3. `optimizer.solve` 로 우선순위별(시간/도보/비용) 방문 순서를 계산해 같은 `group_id` 의 코스 3개를 저장합니다.
   - 각 구간의 이동시간 출처는 `stops[].travel_source`(`tmap`/`cache`/`estimate`/`same`)로 저장되며, 코스 응답의 `has_estimated_travel` 로 추정값 포함 여부를 알 수 있습니다.
   - 재계획(`replan`)은 이전에 제외된 장소도 현재 위치·시각 기준으로 다시 시도합니다.
   - 코스 날짜는 어제보다 이전이면 422 입니다. 요청에 직접 넣은 영업시간(`hours`)도 저장용 영업시간과 같은 검증(휴무일엔 시간 금지, 브레이크는 영업시간 안)을 받습니다.
4. 모든 시각은 출발일 0시부터 지난 분(`*_min`)입니다. 자정을 넘기면 1440 이상이며, `*_time`(HH:MM)과 `*_day_offset` 도 함께 내려갑니다.
5. 그룹 `finalize` 는 **그룹 대표가 저장한 영업시간**을 사용합니다.

## 테스트

```bash
cd backend
pytest                      # SQLite(메모리)로 실행. DB/키 불필요
# 실제 PostgreSQL 로 돌리려면 (이 DB 의 테이블이 삭제되므로 개발용 DB 와 다른 DB 를 쓰세요)
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/routeon_test pytest
```

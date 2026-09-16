# Route-ON — 대중교통·도보 이동시간과 영업시간을 반영한 동선 최적화 서비스

작성일: 2026-09-16
대상 서비스: Route-ON — 시간창 제약 기반 여행·데이트 코스 스케줄러
기술 스택: React, FastAPI, Google OR-Tools, PostgreSQL/PostGIS, Kakao API, Tmap API

## 1. 서비스 설계 요약

본 서비스는 사용자가 방문하고 싶은 장소들을 입력하면, 단순 최단 거리가 아니라 **가게 영업시간·브레이크타임(시간창 제약)** 과 **국내 대중교통 환승 소요시간**까지 반영해 실제로 실행 가능한 방문 순서를 자동으로 계산해주는 앱이다. 기존 여행 플래너(Wanderlog, 구글맵 등)는 최단 경로 위주로 동선을 제안할 뿐, "이 가게는 15시 브레이크타임"이나 "환승에 12분 걸림" 같은 현실적 제약은 반영하지 못한다는 한계가 있다.

핵심 차별점은 문제를 단순 TSP가 아니라 **시간창 제약이 있는 TSP(TSPTW, Traveling Salesman Problem with Time Windows)** 로 정식화하고, 일정이 실제로 지연되었을 때 **남은 구간만 재계산하는 동적 재계획**까지 지원한다는 점이다. 따라서 개발 설계도 `장소 입력 → 영업시간 확보 → 이동시간 매트릭스 계산 → TSPTW 최적화 → 코스 확정 → 실시간 지연 대응(동적 재계획)` 흐름을 중심으로 구성한다.

## 2. 핵심 기능 우선순위

### MVP 필수 기능

1. **카카오 소셜 로그인**
   - Kakao OAuth 2.0으로 인증 후, 서비스 자체 JWT 세션을 발급한다.

2. **장소 입력 (검색 자동완성)**
   - Kakao 로컬 API로 상호명 검색 → 좌표 자동 입력.

3. **영업시간 사용자 직접 입력**
   - 카카오 API가 영업시간을 제공하지 않으므로 사용자가 직접 입력한다.
   - 코스 생성 시 날짜를 먼저 선택해 요일을 고정하고, 해당 요일 영업시간만 입력받는다.
   - 크라우드소싱 없이 `(사용자, 장소, 요일)` 단위로 본인 계정에만 저장·재사용한다 (허위 정보 입력 리스크 방지).

4. **TSPTW 최적화 엔진**
   - Google OR-Tools Routing 모듈로 시간창 제약을 반영한 최적 방문 순서를 계산한다.
   - 본 서비스의 핵심 기술적 차별점.

5. **대중교통 환승 최적화**
   - Tmap 대중교통 API + Kakao Mobility API로 버스-지하철 환승 소요시간을 반영한다.
   - 서비스 범위는 데이터 안정성을 위해 서울로 한정한다.

6. **체류시간 자동 추천**
   - 장소 유형(카페/맛집/전시 등)에 따라 평균 체류시간을 자동 제안한다.

7. **코스 저장 + 링크 공유**
   - UUID 기반 코스 링크를 발급해 비로그인 사용자도 읽기 전용으로 조회할 수 있다.

8. **일정 타임라인 UI / 지도 경로 시각화**
   - Kakao Maps SDK로 마커와 이동 경로를 지도 위에 표시한다.

### 2차 개발 기능

1. **우선순위 비교 뷰 (다중 목적 최적화)**
   - 이동시간/도보량/교통비 우선순위별 여러 코스 variant를 동시에 비교한다.

2. **동선 동적 재계획 (Dynamic Re-planning)**
   - "30분 더 머무르기" / "현재 위치에서 다시 계산" 버튼으로 남은 구간만 재최적화한다.
   - 자율주행의 로컬 플래닝처럼 동적 환경 변화에 적응하는 재계획 역량을 보여주는 기능.

3. **그룹 코스 (투표 기반)**
   - 멤버들이 후보 장소를 등록하고 투표, 득표순 상위 장소가 TSPTW 엔진 입력값이 된다.
   - REST 기반(투표 마감 후 새로고침)으로 구현해 스코프를 안전하게 유지한다.

4. **코스 히스토리 / 날씨 표시 / 코스 피로도 지표 / 예상 비용 계산**
   - 과거 코스 재조회, 기상청 날씨 예보, 총 이동거리 기반 체력 등급, 소액 지출 합산 기능.

## 3. 전체 아키텍처 방향

```text
React + Kakao Maps SDK (Frontend)
  |
  | REST API (HTTPS/JSON)
  v
FastAPI (Backend API)
  |
  |-- 인증: Kakao OAuth 2.0 + JWT
  |
  |-- 최적화 엔진 모듈 (API와 분리)
  |     - Google OR-Tools Routing (TSPTW)
  |     - 동적 재계획 로직
  |
  |-- 외부 API 연동
  |     - Kakao 로컬/Maps/Mobility
  |     - Tmap 대중교통 API
  |     - 기상청 공공데이터 API
  |
  v
PostgreSQL + PostGIS
  - 사용자, 장소, 영업시간, 코스, 그룹/투표 데이터
```

최적화 엔진은 API 구조와 분리된 모듈로 구성해, 추후 다중 목적 최적화나 알고리즘 교체 시 API 구조를 건드리지 않고 로직만 바꿀 수 있도록 설계한다.

## 4. 스택별 개발 로드맵

### 4.1 Frontend: React

#### 설계 방향

"장소 입력 → 코스 확인"까지의 전환을 짧게 만드는 데 집중한다. 첫 화면은 검색·장소 목록 중심으로 구성하고, 결과 화면은 지도 경로와 시간대별 타임라인 카드가 함께 보이도록 설계한다.

#### 주요 화면

1. **로그인 화면** — Kakao OAuth 진입
2. **장소 입력 화면** — 검색 자동완성, 방문 날짜 선택(요일 고정), 영업시간 입력 폼
3. **코스 결과 화면** — 지도 위 경로 시각화 + 우선순위별 코스 variant 비교
4. **일정 타임라인 화면** — 시간순 방문 순서, 동적 재계획 버튼("30분 더 머무르기" 등)
5. **그룹 코스 화면** — 후보 등록, 투표, 득표 현황
6. **코스 히스토리 / 마이페이지** — 저장한 코스 재조회, 복제

#### 상태 관리 전략

컴포넌트 수가 많지 않은 초기 단계에는 React Context + `useReducer` 조합으로 시작하고, 상태가 복잡해지면 **Zustand** 도입을 권장한다. Redux보다 보일러플레이트가 적어 팀 전체가 Git과 React를 동시에 처음 배우는 상황에 적합하다.

권장 상태 단위:

- `PlaceInputState`: 사용자가 입력한 장소, 좌표, 영업시간
- `CourseVariantState`: 우선순위별로 계산된 코스 후보들
- `TimelineState`: 확정된 코스의 시간대별 순서
- `GroupSessionState`: 그룹 후보 장소, 투표 현황
- `UserState`: 로그인 정보, JWT 토큰

#### React 개발 순서

1. 프로젝트 생성, 라우팅 구조, Kakao OAuth 로그인 연동
2. 공통 컴포넌트(버튼, 카드, 지도 마커) 작성
3. 장소 입력 + 영업시간 입력 폼 구현
4. Kakao Maps SDK 연동, 경로 시각화
5. 코스 결과/우선순위 비교 화면 구현
6. 일정 타임라인 + 동적 재계획 버튼 구현
7. 그룹 코스 + 투표 화면 구현
8. 코스 히스토리, 반응형 스타일 정리
9. API 에러/로딩/빈 결과 상태 처리

### 4.2 Backend: FastAPI

#### 주요 모듈

- `auth`: Kakao OAuth 처리, JWT 발급/검증
- `places`: 장소 검색, 좌표 조회, 영업시간 CRUD
- `courses`: 코스 생성, TSPTW 최적화 요청, 코스 저장/공유
- `groups`: 그룹 세션, 후보 등록, 투표
- `weather`: 기상청 API 연동

#### 핵심 API 예시

```http
POST /api/v1/auth/kakao/callback
GET  /api/v1/places/search?query={query}
POST /api/v1/places/{place_id}/business-hours
POST /api/v1/courses/optimize
GET  /api/v1/courses/{share_uuid}
POST /api/v1/courses/{course_id}/replan
POST /api/v1/groups
POST /api/v1/groups/{group_id}/candidates
POST /api/v1/groups/{group_id}/candidates/{candidate_id}/vote
GET  /api/v1/weather?lat={lat}&lng={lng}&date={date}
```

#### TSPTW 최적화 로직

1. 사용자가 선택한 장소 목록, 방문 날짜(요일 고정), 우선순위(이동시간/도보량/교통비)를 입력받는다.
2. 각 장소의 좌표와 저장된 영업시간(없으면 사용자 입력 요청)을 확보한다.
3. Tmap/Kakao Mobility API로 장소 간 이동시간 매트릭스를 계산한다 (대중교통 환승시간 포함).
4. OR-Tools RoutingModel에 각 장소의 영업시간을 시간창(Time Window) 제약으로 등록한다.
   - 브레이크타임이 있는 경우 해당 구간을 제외한 구간을 시간창으로 분리 등록한다.
5. 우선순위에 따라 목적함수 가중치(이동시간/도보량/교통비)를 조정해 Solve한다.
6. 시간 내 방문이 불가능한 장소가 있으면 제외를 추천하는 응답을 반환한다.
7. 결과로 방문 순서, 장소별 도착·출발 예상 시각, 총 이동시간/비용/도보량을 반환한다.

#### 동적 재계획 로직

1. 사용자가 "30분 더 머무르기" 등 지연을 알리면 현재 시각과 남은 장소 목록을 서버로 전송한다.
2. **전체 코스를 처음부터 재계산하지 않고, 현재 시점 이후의 남은 노드만 서브 문제로 재계산한다.**
3. 남은 장소들의 영업시간을 재검증해 시간 내 방문이 불가능해진 장소는 제외를 추천한다.
4. 재계산된 순서와 예상 시각을 반환한다.

## 5. Database: PostgreSQL / PostGIS

### 설계 방향

공간 쿼리(좌표, 거리 계산)가 핵심이므로 PostGIS 확장을 전제로 설계한다. 영업시간은 공유 DB가 아니라 `(사용자, 장소, 요일)` 단위로 개인 계정에만 저장해, 크라우드소싱형 허위 정보 입력 리스크를 원천 차단한다.

### 핵심 테이블 초안

```sql
users
- id
- kakao_uid
- nickname
- created_at

places
- id (kakao place_id)
- name
- latitude
- longitude
- geom
- category

business_hours
- id
- user_id       -- FK, 입력한 본인에게만 귀속
- place_id       -- FK
- weekday
- open_time
- close_time
- break_start
- break_end

courses
- id
- owner_user_id  -- FK
- title
- date
- share_uuid
- priority_type   -- time / walk / cost

course_stops
- id
- course_id      -- FK
- place_id       -- FK
- visit_order
- stay_duration_min
- expected_cost

group_sessions
- id
- course_id      -- FK
- invite_code
- created_at

group_candidate_places
- id
- group_id       -- FK
- place_id       -- FK
- added_by_user_id -- FK

votes
- id
- candidate_id   -- FK
- user_id        -- FK
```

### PostGIS 활용 포인트

- 장소 간 거리 계산: `ST_Distance(geom, target_geom)`
- 반경 내 장소 탐색(향후 추천 기능 확장 시): `ST_DWithin(geom, user_geom, radius)`
- 지도 마커 클러스터링

## 6. API 명세 작성 기준

모든 API는 React 프론트가 안정적으로 사용할 수 있도록 JSON 응답 구조를 고정한다.

공통 응답 예시:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

에러 응답 예시:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "PLACE_UNREACHABLE_IN_TIME",
    "message": "선택한 장소 중 일부는 영업시간 내 방문이 불가능합니다."
  }
}
```

API 문서는 FastAPI Swagger를 기본으로 사용한다.

## 7. 개발 단계별 일정 (총 15주)

### 1단계: 설계 및 기반 구축 (1~4주)

- 요구사항 정의, 와이어프레임/API 명세 확정
- DB 설계(ERD) 확정

### 2단계: 백엔드·프론트 병렬 개발 (5~8주)

- 백엔드: TSPTW 알고리즘 프로토타입, API 개발(CRUD), Kakao/Tmap/기상청 API 연동
- 프론트: API 명세 기반 기본 UI 개발, 지도/타임라인 UI 구현
- API 명세를 먼저 확정해두었기 때문에 프론트는 백엔드 완성을 기다리지 않고 목업 데이터로 병렬 진행 가능

### 3단계: 핵심 차별화 기능 구현 (8~11주)

- 영업시간 입력 기능(백엔드 저장 로직 + 프론트 입력 UI)
- 우선순위 비교·동적 재계획 로직 및 UI 연동
- 그룹 코스 투표 API 및 UI

### 4단계: 부가기능 및 통합 (9~13주)

- 코스 히스토리, 날씨 표시, 비용 계산 등 부가기능
- 통합 및 QA 테스트

### 5단계: 시연 안정화 (13~15주)

- 반응형 점검/배포 마무리
- 발표 자료 및 시연 준비

## 8. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| 카카오 로컬 API가 영업시간 데이터를 제공하지 않음 | 최적화 입력 데이터 부재 | 사용자 직접 입력 방식, 날짜→요일 고정으로 입력 부담 최소화 |
| 영업시간 크라우드소싱 시 허위 정보 입력 위험 | 잘못된 코스 생성 | 공유 DB 미사용, `(사용자,장소,요일)` 단위 개인 저장 |
| 지방 지역 대중교통 데이터 확보 어려움 | 서비스 정확도 저하 | 서비스 범위를 서울로 한정 |
| 실시간 재계산의 서버 부하/구현 복잡도 | 응답 지연 | WebSocket 대신 REST 재요청 방식, 남은 노드만 재계산 |
| 그룹 투표 중복 투표 | 결과 신뢰성 저하 | 계정 기반 1인 1표 제한 |
| 실제 일정 지연 등 돌발 상황 대응 부재 | 사용자 이탈 | 동선 동적 재계획 기능으로 대응 |

## 9. 배포 및 운영 방향

### 개발 환경

- Frontend: React (npm run dev)
- Backend: FastAPI (Uvicorn)
- DB: PostgreSQL + PostGIS Docker 컨테이너
- 최적화 엔진: Google OR-Tools (Python 패키지)

### 운영 환경

- Docker + AWS 프리티어(EC2) 또는 Vercel로 배포
- GitHub Actions로 CI 구성
- 외부 API(Kakao/Tmap/기상청) 응답은 캐싱하여 호출 제한 문제를 줄인다

## 10. 다음 작업 체크리스트

1. API 명세서를 `docs/api_spec.md`로 분리 작성
2. PostgreSQL ERD를 실제 마이그레이션 파일로 확정
3. React 화면 와이어프레임 작성
4. FastAPI 프로젝트와 DB 마이그레이션 구조 먼저 구성
5. Kakao/Tmap/기상청 API 키 발급 현황 정리
6. OR-Tools 기반 TSPTW 프로토타입 구현 착수

---

작업 방식(브랜치 전략, PR 규칙 등)은 [CONTRIBUTING.md](./CONTRIBUTING.md)를 확인하세요.

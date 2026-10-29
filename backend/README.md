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
| `JWT_SECRET_KEY` | JWT 서명 키 | 운영 환경에서는 반드시 변경 |
| `JWT_ALGORITHM` | JWT 알고리즘 | 기본 `HS256` |
| `KAKAO_REST_API_KEY` | 카카오 로컬/로그인 REST API | 카카오 개발자 콘솔에서 발급 |
| `TMAP_APP_KEY` | Tmap 대중교통 API | |
| `KMA_API_KEY` | 기상청 공공데이터 API | |

프론트엔드 변수는 `frontend/.env`에 두며 이름이 `VITE_`로 시작합니다. (`VITE_KAKAO_JAVASCRIPT_KEY`: 카카오 JavaScript 키)

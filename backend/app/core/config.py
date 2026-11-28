from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 실행 환경: "development" | "production". production 이면 기본 JWT 키로는 서버가 뜨지 않습니다.
    app_env: str = "development"

    # DB 연결 정보 - 실제 값은 .env 파일에 작성하고 절대 커밋하지 않습니다.
    database_url: str = "postgresql://postgres:postgres@localhost:5432/routeon"

    # 프론트엔드 주소(쉼표로 여러 개). CORS 허용 목록으로 쓰입니다.
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"

    # 외부 API 키 - 각자 발급받은 키를 .env에 넣어서 사용합니다.
    kakao_rest_api_key: str = ""
    kakao_app_id: str = ""  # 설정하면 카카오 로그인 때 '우리 앱에서 발급된 토큰'인지 검증합니다.
    tmap_app_key: str = ""  # 비어 있으면 이동시간을 직선거리 기반 추정값으로 계산합니다.
    kma_api_key: str = ""  # 기상청 공공데이터 (단기예보)

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 기본 7일

    class Config:
        env_file = ".env"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

DEFAULT_JWT_SECRET = "change-me-in-env"


def check_production_settings(s: Settings = settings) -> None:
    """운영 환경에서 기본 JWT 키를 쓰면 시작 단계에서 막습니다."""
    if s.app_env.lower() == "production" and s.jwt_secret_key == DEFAULT_JWT_SECRET:
        raise RuntimeError("APP_ENV=production 에서는 JWT_SECRET_KEY 를 반드시 바꿔야 합니다")

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DB 연결 정보 - 실제 값은 .env 파일에 작성하고 절대 커밋하지 않습니다.
    database_url: str = "postgresql://postgres:postgres@localhost:5432/routeon"

    # 외부 API 키 - 각자 발급받은 키를 .env에 넣어서 사용합니다.
    kakao_rest_api_key: str = ""
    tmap_app_key: str = ""
    kma_api_key: str = ""  # 기상청 공공데이터

    jwt_secret_key: str = "change-me-in-env"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, courses, groups, health, places, weather
from app.core.config import check_production_settings, settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    check_production_settings()  # production 에서 기본 JWT 키면 여기서 서버 시작이 실패합니다.
    yield


app = FastAPI(title="Route-ON API", version="0.2.0", lifespan=lifespan)

# 프론트엔드(React)에서의 요청을 허용합니다. 주소는 .env 의 CORS_ORIGINS 로 바꿉니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(places.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(groups.router, prefix="/api/v1")
app.include_router(weather.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": "Route-ON API", "status": "running"}

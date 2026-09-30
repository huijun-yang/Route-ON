from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health

app = FastAPI(title="Route-ON API", version="0.1.0")

# 프론트엔드(React, 개발 서버 기준)에서의 요청을 허용합니다.
# 실제 배포 시 origins는 프론트 배포 주소로 교체해야 합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": "Route-ON API", "status": "running"}

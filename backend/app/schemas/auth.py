from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class KakaoLoginRequest(BaseModel):
    """프론트가 Kakao.Auth.getAccessToken() 으로 얻은 카카오 액세스 토큰."""

    access_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str  # 서비스 자체 JWT
    token_type: Literal["bearer"] = "bearer"
    user: UserRead

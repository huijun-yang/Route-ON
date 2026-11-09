import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import KakaoLoginRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.kakao import (
    KakaoAuthError,
    KakaoServiceError,
    fetch_kakao_profile,
    get_kakao_client,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/kakao", response_model=TokenResponse)
def login_with_kakao(
    body: KakaoLoginRequest,
    db: Session = Depends(get_db),
    client: httpx.Client = Depends(get_kakao_client),
):
    """카카오 액세스 토큰을 검증하고, 사용자를 저장(없으면 생성)한 뒤 서비스 JWT 를 발급합니다."""
    try:
        profile = fetch_kakao_profile(body.access_token, client)
    except KakaoAuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid kakao access token")
    except KakaoServiceError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="kakao service unavailable")

    def find_user() -> User | None:
        return db.scalar(select(User).where(User.kakao_id == profile.kakao_id))

    user = find_user()
    if user is None:
        user = User(kakao_id=profile.kakao_id, nickname=profile.nickname, email=profile.email)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # 같은 사용자가 동시에 처음 로그인한 경우: 먼저 저장된 사용자를 사용합니다.
            db.rollback()
            user = find_user()
            if user is None:
                raise
    else:
        user.nickname = profile.nickname
        if profile.email is not None:  # 이메일 동의를 철회해도 기존 값은 지우지 않습니다.
            user.email = profile.email
        db.commit()

    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    """JWT 로 로그인 상태를 확인합니다. (로그인이 필요한 API 의 예시)"""
    return current_user

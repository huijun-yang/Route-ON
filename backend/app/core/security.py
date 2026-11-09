from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


class InvalidTokenError(Exception):
    """JWT 가 잘못되었거나 만료되었을 때 발생합니다."""


def create_access_token(user_id: str) -> str:
    """서비스 자체 JWT 를 발급합니다. sub 에 사용자 ID 를 담습니다."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """JWT 를 검증하고 사용자 ID(sub)를 반환합니다."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise InvalidTokenError("invalid or expired token")
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise InvalidTokenError("token has no subject")
    return user_id

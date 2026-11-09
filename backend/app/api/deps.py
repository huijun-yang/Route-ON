from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import InvalidTokenError, decode_access_token
from app.models import User

# auto_error=False: 토큰이 없을 때 403 대신 아래에서 401 로 통일해서 응답합니다.
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """로그인이 필요한 API 에서 Depends(get_current_user) 로 사용합니다."""
    if credentials is None:
        raise _unauthorized("not authenticated")
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise _unauthorized("invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("user not found")
    return user

"""로컬 개발용 JWT 발급 스크립트.

카카오 로그인 없이 Swagger(/docs)에서 로그인이 필요한 API 를 시험할 때 사용합니다.
로컬 DB 에 'dev-local' 테스트 사용자를 만들고(이미 있으면 재사용) 그 사용자의 JWT 를 출력합니다.

실행 (backend 폴더에서, 가상환경을 켠 상태):
    python -m scripts.dev_token

출력된 토큰을 http://localhost:8000/docs 오른쪽 위 Authorize 에 붙여넣으면 됩니다.
개발 전용이므로 운영 DB 에서는 실행하지 마세요.
"""
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models import User

DEV_KAKAO_ID = "dev-local"


def main() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.kakao_id == DEV_KAKAO_ID))
        if user is None:
            user = User(kakao_id=DEV_KAKAO_ID, nickname="개발용 테스트")
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"사용자: {user.nickname} (id={user.id})")
        print("아래 토큰을 Swagger 의 Authorize 에 붙여넣으세요.\n")
        print(create_access_token(user.id))


if __name__ == "__main__":
    main()

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# create_engine 은 실제 요청이 올 때 연결하므로, import 시점에는 DB가 꺼져 있어도 오류가 나지 않습니다.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """요청마다 DB 세션을 열고, 응답이 끝나면 닫습니다.

    사용 예:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

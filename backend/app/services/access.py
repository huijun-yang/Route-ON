"""코스/그룹 접근 권한 확인."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, GroupMember, GroupSession


def can_view_course(db: Session, user_id: str, course: Course) -> bool:
    """코스 주인이거나, 이 코스(3개 버전 중 하나)가 연결된 그룹의 멤버면 볼 수 있습니다."""
    if course.owner_user_id == user_id:
        return True
    sibling_ids = select(Course.id).where(Course.group_id == course.group_id)
    stmt = (
        select(GroupMember.user_id)
        .join(GroupSession, GroupSession.id == GroupMember.group_session_id)
        .where(GroupSession.course_id.in_(sibling_ids), GroupMember.user_id == user_id)
    )
    return db.scalar(stmt) is not None

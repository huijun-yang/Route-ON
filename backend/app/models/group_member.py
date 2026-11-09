from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GroupMember(Base):
    """초대코드로 그룹에 참여한 멤버. role이 'owner'인 사람이 대표(영업시간 입력 담당)."""

    __tablename__ = "group_members"

    group_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("group_sessions.id"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # "owner" | "member"
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

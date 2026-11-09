from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, gen_uuid


class GroupSession(Base):
    __tablename__ = "group_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    # 투표가 끝나 코스가 만들어지기 전에는 코스가 없으므로 비워둘 수 있어야 함
    course_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("courses.id"), unique=True, nullable=True
    )
    invite_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open")  # "open" | "closed"

    course: Mapped["Course | None"] = relationship(back_populates="group_session")
    candidate_places: Mapped[list["GroupCandidatePlace"]] = relationship(back_populates="group_session")

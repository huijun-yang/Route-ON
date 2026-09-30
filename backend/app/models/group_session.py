from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, gen_uuid


class GroupSession(Base):
    __tablename__ = "group_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), unique=True, nullable=False)
    invite_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open")  # "open" | "closed"

    course: Mapped["Course"] = relationship(back_populates="group_session")
    candidate_places: Mapped[list["GroupCandidatePlace"]] = relationship(back_populates="group_session")
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, gen_uuid


class GroupCandidatePlace(Base):
    __tablename__ = "group_candidate_places"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    group_session_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_sessions.id"), nullable=False)
    place_id: Mapped[str] = mapped_column(String(50), ForeignKey("places.kakao_place_id"), nullable=False)
    added_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    group_session: Mapped["GroupSession"] = relationship(back_populates="candidate_places")
    place: Mapped["Place"] = relationship()
    votes: Mapped[list["Vote"]] = relationship(back_populates="candidate_place")
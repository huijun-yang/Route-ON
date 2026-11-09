from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, gen_uuid


class Vote(Base):
    __tablename__ = "votes"
    # 같은 사람이 같은 후보에 중복 투표하지 못하게 막음
    __table_args__ = (
        UniqueConstraint("candidate_place_id", "user_id", name="uq_votes_candidate_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    candidate_place_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("group_candidate_places.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    candidate_place: Mapped["GroupCandidatePlace"] = relationship(back_populates="votes")
